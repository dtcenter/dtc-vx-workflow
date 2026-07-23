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


def ensprob_bin_width(num_ens_members):
    """Return the METplus probability-bin-width threshold string for an N-member ensemble.

    An N-member ensemble can only produce ensemble relative frequencies of k/N (k = 0..N), so the
    natural probability bin width is 1/N (e.g. N=10 -> '==0.1', N=20 -> '==0.05'). This is used
    both for the per-variable FCST_VARn_THRESH and for the tool-level FCST_<tool>_PROB_THRESH.
    """
    if not num_ens_members:
        raise ValueError("num_ens_members must be a positive integer")
    return f"=={1.0 / num_ens_members:g}"


def make_ensprob_var_list(vx_config_dict, field_group, num_ens_members=None,
                          level="all", thresh="all", prob_thresh=None):
    """Render the FCST/OBS variable list for ensemble-probability (ensprob) verification of the
    ensemble relative-frequency fields produced by GenEnsProd.

    Unlike make_var_list() (which emits one FCST/OBS pair per field with thresholds comma-joined),
    ensprob verification emits, for EACH forecast threshold, a separate FCST/OBS pair -- and does
    so in two passes over all thresholds:

      1. Probabilistic pass: the GenEnsProd frequency field is verified as a probability (yields
         Brier/reliability/ROC via the PCT/PSTD/PJC line types).
      2. Scalar pass: the same field is verified as a scalar (``prob = FALSE``) using neighborhood
         methods (yields NBRCNT/NBRCTC).

    All probabilistic pairs are emitted first, then all scalar pairs, matching MET's expectation.
    A single running counter drives the ``VARn`` index so it stays contiguous starting at 1 even
    when the level/threshold filters skip entries.

    The forecast field name must exactly match GenEnsProd's output-variable naming, which appends
    the level and the physical threshold to the field name:

        {fcst_name}_{level}_ENS_FREQ_{thresh}

    For accumulated fields the accumulation period is expected to be part of ``fcst_name`` already
    (e.g. ``APCP_06``), so no special-casing is required here.

    The forecast THRESH is a probability bin width, NOT the physical threshold. By default it is
    derived from the ensemble size as ``1/num_ens_members``, since an N-member ensemble can only
    produce relative frequencies of k/N (k = 0..N); pass ``prob_thresh`` to override.

    Per-entry keys used (in addition to those documented in make_var_list()):

      nbrhd_options (str): Neighborhood option string appended to ``OBS_VARn_OPTIONS`` on the
                           scalar pass only (optional).

    Note that the entry's ``fcst_options`` are intentionally NOT applied here: for ensprob the
    forecast field is the ENS_FREQ probability field, so the only forecast option is ``prob =
    FALSE`` on the scalar pass.
    """
    lgr = logging.getLogger(__name__)

    if field_group not in vx_config_dict:
        raise ValueError(f"Provided field group {field_group} is not in field config dictionary")

    if prob_thresh is None:
        if not num_ens_members:
            raise ValueError(
                "make_ensprob_var_list requires num_ens_members (to derive the probability bin "
                "width) unless prob_thresh is given explicitly")
        prob_thresh = ensprob_bin_width(num_ens_members)
    lgr.debug(f"{prob_thresh=}")

    var_list = ''
    i = 0
    # Loop over each field twice: first treating the forecast field as probabilistic, then as a
    # scalar (with prob=FALSE and neighborhood options).
    for treat_as_prob in (True, False):
        for entry in vx_config_dict[field_group]:
            lgr.debug(f"{entry=}")
            fcstvar = entry["fcst_name"]
            obsvar = entry.get("obs_name", fcstvar)
            fcst_levels = list(entry["fcst_levels"])
            obs_levels = list(entry.get("obs_levels", fcst_levels))
            if len(obs_levels) != len(fcst_levels):
                raise ValueError(
                    f"For field '{fcstvar}' in group '{field_group}', 'obs_levels' "
                    f"(length {len(obs_levels)}) must be the same length as 'fcst_levels' "
                    f"(length {len(fcst_levels)})")
            fcst_threshes = entry.get("fcst_thresholds", [])
            obs_threshes = entry.get("obs_thresholds", fcst_threshes)
            if len(obs_threshes) != len(fcst_threshes):
                raise ValueError(
                    f"For field '{fcstvar}' in group '{field_group}', 'obs_thresholds' "
                    f"(length {len(obs_threshes)}) must be the same length as 'fcst_thresholds' "
                    f"(length {len(fcst_threshes)})")
            base_obs_opts = entry.get("obs_options")
            nbrhd_opts = entry.get("nbrhd_options")

            for li, level_fcst in enumerate(fcst_levels):
                if level != "all" and level != level_fcst:
                    continue
                level_obs = obs_levels[li]
                for ti, thresh_fcst in enumerate(fcst_threshes):
                    if thresh not in ("all", "none") and thresh != thresh_fcst:
                        continue
                    # Increment only after passing the skip checks so VARn stays contiguous
                    i += 1
                    # MET field names cannot contain '&&' or '||'
                    thresh_name = thresh_fcst.replace("&&", ".and.").replace("||", ".or.")

                    fcst_var = f"FCST_VAR{i}_NAME = {fcstvar}_{level_fcst}_ENS_FREQ_{thresh_name}\n"
                    fcst_var += f"FCST_VAR{i}_LEVELS = {level_fcst}\n"
                    fcst_var += f"FCST_VAR{i}_THRESH = {prob_thresh}\n"
                    if not treat_as_prob:
                        fcst_var += f"FCST_VAR{i}_OPTIONS = prob = FALSE;\n"

                    obs_var = f"OBS_VAR{i}_NAME = {obsvar}\n"
                    obs_var += f"OBS_VAR{i}_LEVELS = {level_obs}\n"
                    if thresh != "none":
                        obs_var += f"OBS_VAR{i}_THRESH = {obs_threshes[ti]}\n"
                    # Base obs options apply on both passes; the neighborhood clause is added only
                    # on the scalar pass.
                    obs_opts = [o.rstrip() for o in
                                (base_obs_opts, None if treat_as_prob else nbrhd_opts) if o]
                    if obs_opts:
                        obs_var += f"OBS_VAR{i}_OPTIONS = {' '.join(obs_opts)}\n"

                    var_list += fcst_var + obs_var + "\n"
                    lgr.debug(f"{fcst_var=}")
                    lgr.debug(f"{obs_var=}")

    return var_list

