"""
Common utilities for creating/handling METplus configuration files
"""
import logging
import os
import sys
from jinja2 import Environment, FileSystemLoader


def make_var_lists(vx_config_dict,field_group):
    """Renders two multi-line strings representing the list of forecast and observation variables
    (respectively) as expected by METplus in a .conf file. For each field group, the variables are
    read from the provided dictionary (read in from dtc-vx-workflow/parm/metplus/vx_configs/*yaml)
    and each key is a string separated by a special delimiter string (delim_str) that can be
    optionally split into the variable name for the forecast and observation files respectively.
    In addition, the value corresponding to each key is a dictionary with a key for each variable
    (again optionally split with delim_str) with a value that is a list representing threshold
    values for METplus to verify against.

    The output will be two multiline strings representing the list of forecast and obs variables,
    levels, and (optionally) thresholds.

    Example:

      vx_config_dict entry:

      SFC:
          TMP:
              Z2: []
          DPT:
              Z2: []

      fcst_var_list:

      FCST_VAR1_NAME = TMP
      FCST_VAR1_LEVELS = Z2
      FCST_VAR2_NAME = DPT
      FCST_VAR2_LEVELS = Z2

      obs_var_list:

      OBS_VAR1_NAME = TMP
      OBS_VAR1_LEVELS = Z2
      OBS_VAR2_NAME = DPT
      OBS_VAR2_LEVELS = Z2
    """
    lgr = logging.getLogger(__name__)

    delim_str="%%"

    i=1
    fcst_var_list=''
    obs_var_list=''
    for var,levdic in vx_config_dict[field_group].items():
        for lev in levdic:
          print(f"{var=}")
          print(f"{levdic=}")
          print(f"{lev=}")
          split=var.split(delim_str)
          if len(split)==2:
              fcstvar=split[0]
              obsvar=split[1]
          elif len(split)==2:
              fcstvar=obsvar=split[0]
          else:
              raise ValueError("vx config dict entry {var} in field group {field_group} is malformed, maybe too many %% entries?")
  
          split=lev.split(delim_str)
          if len(split)==2:
              fcstlev=split[0]
              obslev=split[1]
          elif len(split)==2:
              fcstlev=obslev=split[0]
          else:
              raise ValueError("vx config dict entry {lev} in field group {field_group} is malformed, maybe too many %% entries?")
  
          fcst_var_list+=f"FCST_VAR{i}_NAME = {fcstvar}\n"
          fcst_var_list+=f"FCST_VAR{i}_LEVELS = {fcstlev}\n"
          obs_var_list+=f"OBS_VAR{i}_NAME = {obsvar}\n"
          obs_var_list+=f"OBS_VAR{i}_LEVELS = {obslev}\n"
          lgr.debug(f"{fcst_var_list=}")
          lgr.debug(f"{obs_var_list=}")
          i+=1

    return fcst_var_list,obs_var_list

def render_metplus_confs(cfg,settings,template_fn,vx_leadhr_list,tasks):
    """Renders metplus conf files from the appropriate template and user settings.
    If VX_TASKS > 1 and vx_leadhr_list > 1, renders a conf file for each parallel task.
    Returns the filename(s) of metplus conf files that were rendered"""

    logger = logging.getLogger(__name__)

    num_fhrs = len(vx_leadhr_list)
    outconfs = []
    logger.debug(f"Loading METplus conf template file: {template_fn}")
    logger.debug(f"from directory {cfg['user']['METPLUS_CONF']}")
    env = Environment(loader=FileSystemLoader(cfg['user']['METPLUS_CONF']))
    template = env.get_template(template_fn)

    if tasks > 1:
        # Break down forecast hours according to number of tasks requested
        if tasks > num_fhrs:
            logger.warning("Number of tasks is greater than number of forecast hours\n"\
                           f"Only running {num_fhrs} tasks in parallel")
            tasks = len(vx_leadhr_list)

        for i in range(tasks):
            logger.debug(f"Rendering conf file for task {i}")
            # We will have i conf files, so append i to the base filename for each
            settings['metplus_log_fn'] = f"{settings['metplus_log_fn'].rsplit('.',1)[0]}.{i}"
            settings['metplus_config_fn'] = f"{settings['metplus_config_fn'].rsplit('.',1)[0]}.{i}"
            outconf = f"{settings['output_dir']}/{settings['metplus_config_fn']}"
            logger.debug(f"metplus log file for task: {settings['metplus_log_fn']}")
            logger.debug(f"metplus final rendered conf for task: {outconf}")
            hours_per_task,remainder = divmod(num_fhrs,tasks)
            if settings.get("staging_dir"):
                settings['staging_dir'] = f"{settings['staging_dir']}.{i}"
            # For cases where things don't divide evenly, ensure we get best distribution
            if i >= remainder:
                vx_leadhr_list, task_fhrs = vx_leadhr_list[hours_per_task:],vx_leadhr_list[:hours_per_task]
            else:
                vx_leadhr_list, task_fhrs = vx_leadhr_list[hours_per_task+1:],vx_leadhr_list[:hours_per_task+1]
            settings['vx_leadhr_list'] = ', '.join(map(str,task_fhrs))
            logger.debug(f"Task {i} will process lead hours: {settings['vx_leadhr_list']}")
            rendered = template.render(settings)
            with open(outconf,'w', encoding="utf-8") as f:
                f.write(rendered)
            outconfs.append(outconf)

    else:
        #Remove task-specific suffixes if we're only using one task
        settings['metplus_log_fn'] = settings['metplus_log_fn'].rsplit('.',1)[0]
        settings['metplus_config_fn'] = settings['metplus_config_fn'].rsplit('.',1)[0]
        outconf = f"{settings['output_dir']}/{settings['metplus_config_fn']}"
        logger.debug("Rendering conf file")
        logger.debug(f"metplus log file: {settings['metplus_log_fn']}")
        logger.debug(f"metplus final rendered conf: {settings['metplus_config_fn']}")
        logger.debug(f"Will process lead hours: {vx_leadhr_list}")
        settings['vx_leadhr_list'] = vx_leadhr_list
        rendered = template.render(settings)
        with open(outconf,'w', encoding="utf-8") as f:
            f.write(rendered)
        outconfs = [outconf]

    return outconfs

