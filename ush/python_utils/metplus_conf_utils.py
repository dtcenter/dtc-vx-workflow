"""
Common utilities for creating/handling METplus configuration files
"""
import logging
import os
import sys
from jinja2 import Environment, FileSystemLoader


def make_var_list(vx_config_dict,field_group,level,ens=False):
    """Renders a multi-line string representing the list of forecast and observation variables
    as expected by METplus in a .conf file. For each field group, ``vx_config_dict[field_group]``
    is a LIST of field entries; each entry becomes one ``FCST_VARn`` / ``OBS_VARn`` block. Using a
    list (rather than a dict keyed by forecast field name) allows the same forecast field to appear
    more than once in a group (e.g. surface CAPE and MLCAPE, both with forecast name ``CAPE``).

    Each entry is a dictionary with the following keys:

      fcst_name          (str) : Forecast field name (required).
      obs_name      (str) : Observation field name (optional; defaults to ``fcst_name``).
      fcst_levels       (list) : Forecast levels (required).
      obs_levels   (list) : Observation levels (optional; defaults to ``fcst_levels``; must be the
                            same length as ``fcst_levels`` when provided).
      fcst_thresholds   (list) : Forecast thresholds (optional).
      obs_thresholds(list): Observation thresholds (optional; defaults to ``fcst_thresholds``).
      fcst_options  (str) : Extra METplus options for the forecast field (optional).
      obs_options   (str) : Extra METplus options for the observation field (optional).

    The output is a multiline string representing the list of forecast and obs variables,
    levels, and (optionally) thresholds and options.

    Example:

      vx_config_dict entry:

      SFC:
        - fcst_name: TMP
          fcst_levels: [Z2]
        - fcst_name: DPT
          fcst_levels: [Z2]

      var_list:

      FCST_VAR1_NAME = TMP
      FCST_VAR1_LEVELS = Z2
      OBS_VAR1_NAME = TMP
      OBS_VAR1_LEVELS = Z2

      FCST_VAR2_NAME = DPT
      FCST_VAR2_LEVELS = Z2
      OBS_VAR2_NAME = DPT
      OBS_VAR2_LEVELS = Z2
    """
    lgr = logging.getLogger(__name__)

    if field_group not in vx_config_dict:
        raise ValueError(f"Provided field group {field_group} is not in field config dictionary")

    var_list=''
    ens_var_list=''
    for i, entry in enumerate(vx_config_dict[field_group], start=1):
        lgr.debug(f"{entry=}")
        fcstvar = entry["fcst_name"]
        obsvar = entry.get("obs_name", fcstvar)
        lgr.debug(f"{level=}")
        if level != "all":
            if level not in entry["fcst_levels"]:
                continue
        fcst_levels = list(entry["fcst_levels"])
        obs_levels = list(entry.get("obs_levels", fcst_levels))
        if len(obs_levels) != len(fcst_levels):
            raise ValueError(
                f"For field '{fcstvar}' in group '{field_group}', 'obs_levels' "
                f"(length {len(obs_levels)}) must be the same length as 'levels' "
                f"(length {len(fcst_levels)})")
        lgr.debug(f"{fcst_levels}")
        lgr.debug(f"{obs_levels}")
        if ens:
            ens_var_list+=f"ENS_VAR{i}_NAME = {fcstvar}\n"
            ens_var_list+=f"ENS_VAR{i}_LEVELS = {', '.join(fcst_levels)}\n"
            if entry.get("fcst_thresholds"):
                ens_var_list+=f"ENS_VAR{i}_THRESH = {', '.join(entry['fcst_thresholds'])}\n"
            if opt:=entry.get("fcst_options"):
                ens_var_list+=f"ENS_VAR{i}_OPTIONS = {opt}\n"
            lgr.debug(f"{ens_var_list}")
            continue

        fcst_var_list=f"FCST_VAR{i}_NAME = {fcstvar}\n"
        fcst_var_list+=f"FCST_VAR{i}_LEVELS = {', '.join(fcst_levels)}\n"
        obs_var_list=f"OBS_VAR{i}_NAME = {obsvar}\n"
        obs_var_list+=f"OBS_VAR{i}_LEVELS = {', '.join(obs_levels)}\n"

        # Set threshold variables unless thresh has been set to "none" (or thresholds is an empty list or missing)
        if entry.get("fcst_thresholds"):
            fcst_threshlist = ', '.join(entry["fcst_thresholds"])
            obs_threshlist = ', '.join(entry.get("obs_thresholds", entry["fcst_thresholds"]))
            fcst_var_list+=f"FCST_VAR{i}_THRESH = {fcst_threshlist}\n"
            obs_var_list+=f"OBS_VAR{i}_THRESH = {obs_threshlist}\n"

        if opt:=entry.get("fcst_options"):
            fcst_var_list+=f"FCST_VAR{i}_OPTIONS = {opt}\n"
        if opt:=entry.get("obs_options"):
            obs_var_list+=f"OBS_VAR{i}_OPTIONS = {opt}\n"
        var_list+=fcst_var_list
        var_list+=obs_var_list
        var_list+="\n"

        lgr.debug(f"{fcst_var_list=}")
        lgr.debug(f"{obs_var_list=}")
        lgr.debug(f"{var_list=}")

    lgr.debug(f"Ending {ens_var_list}")

    if ens:
        return ens_var_list

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

