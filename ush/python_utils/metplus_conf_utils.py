"""
Common utilities for creating/handling METplus configuration files
"""
import logging
import os
import sys
from jinja2 import Environment, FileSystemLoader


def make_var_list(vx_config_dict,field_group,level,thresh,accum=0):
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

      var_list:

      FCST_VAR1_NAME = TMP
      FCST_VAR1_LEVELS = Z2
      FCST_VAR2_NAME = DPT
      FCST_VAR2_LEVELS = Z2

      OBS_VAR1_NAME = TMP
      OBS_VAR1_LEVELS = Z2
      OBS_VAR2_NAME = DPT
      OBS_VAR2_LEVELS = Z2
    """
    lgr = logging.getLogger(__name__)

    if field_group not in vx_config_dict:
        raise ValueError("Provided field group {field_group} is not in defined level dictionary {vx_config_dict}")

    i=1
    var_list=''
    for obsvar,levdic in vx_config_dict[field_group].items():
        obslevels=fcstlevels=''
        for lev in levdic:
            if lev == 'fcst_field_name':
                continue
            # Alias dictionary of remaining options for convenience
            ld=levdic[lev]
            lgr.debug(f"{levdic=}")
            lgr.debug(f"{lev=}")
            lgr.debug(f"{ld=}")
            obslevels=f"{lev}, {obslevels}"
            if ld.get("fcst_level_name"):
                fcstlevels=f"{ld.get('fcst_level_name')}, {fcstlevels}"
            else:
                fcstlevels=f"{lev}, {fcstlevels}"

        fcstvar=obsvar
        if levdic.get("fcst_field_name"):
            fcstvar=levdic["fcst_field_name"]
  
        # Some variables need special treatment
        if field_group == "APCP":
            # Remove zeros from level names for precipitation accumulations
            fcstlev=fcstlev.replace('0','')

        fcst_var_list=f"FCST_VAR{i}_NAME = {fcstvar}\n"
        fcst_var_list+=f"FCST_VAR{i}_LEVELS = {fcstlevels}\n"
        if field_group == "APCP" or field_group == "ASNOW":
            obs_var_list=f"OBS_VAR{i}_NAME = {obsvar}_{accum}\n"
        else:
            obs_var_list=f"OBS_VAR{i}_NAME = {obsvar}\n"
        obs_var_list+=f"OBS_VAR{i}_LEVELS = {obslevels}\n"

        # Set threshold variables unless thresh has been set to "none" (or thresholds is an empty list or missing)
        if thresh != "none" and ld.get("thresholds"):
            threshlist = ', '.join(ld["thresholds"])
            fcst_var_list+=f"FCST_VAR{i}_THRESH = {threshlist}\n"
            obs_var_list+=f"OBS_VAR{i}_THRESH = {threshlist}\n"

        if opt:=ld.get("options"):
            obs_var_list+=f"OBS_VAR{i}_OPTIONS = {opt}\n"
        if opt:=ld.get("fcst_options"):
            fcst_var_list+=f"FCST_VAR{i}_OPTIONS = {opt}\n"
        var_list+=fcst_var_list
        var_list+=obs_var_list

        lgr.debug(f"{fcst_var_list=}")
        lgr.debug(f"{obs_var_list=}")
        lgr.debug(f"{var_list=}")
        i+=1

    return var_list

def render_metplus_confs(cfg,settings,template_fn,vx_leadhr_list,tasks,extra=None):
    """Renders metplus conf files from the appropriate template and user settings.
    If VX_TASKS > 1 and vx_leadhr_list > 1, renders a conf file for each parallel task.
    Returns the filename(s) of metplus conf files that were rendered

    vx_leadhr_list (list)
    tasks (int): The number of parallel tasks to prepare conf files for
    extra (dict): A dictionary of additional settings to append to the conf file"""

    logger = logging.getLogger(__name__)

    # initialize extra as an empty dictionary if not provided
    if extra is None:
        extra={}
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
                settings['staging_dir'] = f"{str(settings['staging_dir']).rsplit('.',1)[0]}.{i}"
            # For cases where things don't divide evenly, ensure we get best distribution
            logger.debug(f"{vx_leadhr_list=}")
            if i >= remainder:
                vx_leadhr_list, task_fhrs = vx_leadhr_list[hours_per_task:],vx_leadhr_list[:hours_per_task]
            else:
                vx_leadhr_list, task_fhrs = vx_leadhr_list[hours_per_task+1:],vx_leadhr_list[:hours_per_task+1]
            settings['vx_leadhr_list'] = ', '.join(map(str,task_fhrs))
            logger.debug(f"Task {i} will process lead hours: {settings['vx_leadhr_list']}")
            logger.debug(f"{vx_leadhr_list=}")
            logger.debug(f"{settings['vx_leadhr_list']=}")
            rendered = template.render(settings)
            with open(outconf,'w', encoding="utf-8") as f:
                f.write(rendered)
                # Write additional lines to the end of the conf file
                for k, v in extra.items():
                    logger.debug(f"Adding extra line to conf file: '{k} = {v}'")
                    f.write(f"\n{k} = {v}")
            outconfs.append(outconf)

    else:
        #Remove task-specific suffixes if we're only using one task
        settings['metplus_log_fn'] = settings['metplus_log_fn'].rsplit('.',1)[0]
        settings['metplus_config_fn'] = settings['metplus_config_fn'].rsplit('.',1)[0]
        if settings.get("staging_dir"):
            settings['staging_dir'] = f"{str(settings['staging_dir']).rsplit('.',1)[0]}"
        outconf = f"{settings['output_dir']}/{settings['metplus_config_fn']}"
        logger.debug("Rendering conf file")
        logger.debug(f"metplus log file: {settings['metplus_log_fn']}")
        logger.debug(f"metplus final rendered conf: {settings['metplus_config_fn']}")
        logger.debug(f"Will process lead hours: {vx_leadhr_list}")
        settings['vx_leadhr_list'] = vx_leadhr_list
        rendered = template.render(settings)
        with open(outconf,'w', encoding="utf-8") as f:
            f.write(rendered)
            # Write additional lines to the end of the conf file
            for k, v in extra.items():
                logger.debug(f"Adding extra line to conf file: '{k} = {v}'")
                f.write(f"\n{k} = {v}")
        outconfs = [outconf]

    return outconfs

