# pylint: disable=logging-fstring-interpolation
"""
Converted from gridstat_or_pointstat.sh, this script calls the METplus "GridStat" or "PointStat"
tool depending on the runtime settings, to verify a meteorological forecast against gridded or
point observations respectively.

The script is intended to be called from jobs/GRIDSTAT_OR_POINTSTAT.sh.
"""

import argparse
import logging
import os
import subprocess

from multiprocessing import Pool
from pathlib import Path
from string import Template

import uwtools.api.config as uwconfig

from python_utils import setup_logging, render_metplus_confs
from set_leadhrs import set_leadhrs
from set_vx_params import set_vx_params

def gridstat_or_pointstat(config_file,cdate,obs_dir,field_group,obtype,accum_hh,ensmem_index,
                          fcst_level,fcst_thresh):
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches,too-many-statements
    """
    Execute a METplus ``GridStat`` or ``PointStat`` verification task.

    Parameters
    ----------
    config_file : str
        Path to the experiment YAML configuration file.
    cdate : str
        Eight‑digit cycle date in ``YYYYMMDDHH`` format.
    obs_dir : str
        Directory containing observation files for the chosen ``obtype``.
    field_group : str
        Group of observation fields to verify (e.g., ``APCP``, ``REFC``, ``SFC``).
    obtype : str
        Observation type for this verification task (e.g., ``NOHRSC``, ``CCPA``, ``NDAS``).
    accum_hh : int
        Accumulation hours for the observation type.
    ensmem_index : int
        Index of the ensemble member to process (``0`` for deterministic runs).
    fcst_level : str
        METplus forecast level (e.g., ``L0``, ``A03``).
    fcst_thresh : str
        Forecast threshold set to verify against, usually ``"all"`` or ``"none"``.

    Returns
    -------
    None
        The function runs METplus, potentially in parallel with multiprocessing depending on user
        settings, and exits when all tasks finish.

    Notes
    -----
    * The function reads the experiment configuration, determines whether the verification should
      run in *grid* or *point* mode based on the field geometry defined in the Rocoto task and set
      by the set_vx_params() function, and constructs all the directory and file paths required
      for the METplus run.
    * For each parallel task, it builds a list of valid lead hours, renders a configuration file
      based on the Jinja template in parm/metplus/, and executes the METplus tasks in parallel
      using ``multiprocessing.Pool``.
    * Errors are raised for missing observation directories, empty lead‑hour lists, or unsupported
      task/observation type combinations.
    * A METplus log file is written for each parallel task.
    """
    lgr = logging.getLogger(__name__)

    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    # Set some aliases
    vxcfg = cfg["verification"]
    do_ens = cfg["ensemble"]["DO_ENSEMBLE"]

    # Check that basic input directories exist:
    if not Path(obs_dir).is_dir():
        raise FileNotFoundError(f"{obs_dir=} does not exist or is not a directory")

    # Set various verification parameters associated with the field to be verified, including
    # whether we are running GridStat or Pointstat (geom)
    geom, _, _, met_out_name, met_filedir_name = set_vx_params(obtype,field_group,accum_hh)

    ensmem=f"mem{str(ensmem_index).zfill(vxcfg['VX_NDIGITS_ENSMEM_NAMES'])}"

    # Set ensemble time lag settings
    lgr.debug(f"{cfg['ensemble']['ENS_TIME_LAG_HRS']=}")
    lgr.debug(f"{ensmem_index=}")
    lgr.debug(f"{vxcfg['VX_NDIGITS_ENSMEM_NAMES']=}")
    time_lag = 0
    if do_ens:
        time_lag = cfg['ensemble']['ENS_TIME_LAG_HRS'][ensmem_index]*3600

    # Make a dictionary of variables that may need to be substituted; these will be used to replace
    # bash-like variables in some strings. This is needed to maintain some functionality while we
    # still have a mix of bash and python exscripts.
    subvars = {
            "FIELD_GROUP": field_group,
            "ACCUM_HH": f"{accum_hh:02}",
            "ensmem_name": f"mem{str(ensmem_index).zfill(vxcfg['VX_NDIGITS_ENSMEM_NAMES'])}",
            "time_lag": time_lag,
              }

    # Set paths and file templates for input to and output from the MET/
    # METplus tool to be run as well as other file/directory parameters.

    exptdir=vxcfg["VX_OUTPUT_BASEDIR"]
    if geom == "grid":
        metplus_tool_name = "grid_stat"
        metplus_tool_camel_case = "GridStat"
        if "APCP" in met_filedir_name:
            if do_ens:
                obs_in_dir = Path(exptdir, cdate, "obs", "metprd", "PcpCombine_obs")
                fcst_in_dir = Path(exptdir, cdate, ensmem, "metprd", "PcpCombine_fcst")
            else:
                obs_in_dir = Path(exptdir, cdate, "metprd", "PcpCombine_obs")
                fcst_in_dir = Path(exptdir, cdate, "metprd", "PcpCombine_fcst")
            obs_in_fn_template = Template(
                vxcfg["OBS_CCPA_APCP_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]
            ).substitute(subvars)
            lgr.debug(f"{vxcfg['FCST_FN_TEMPLATE_PCPCOMBINE_OUTPUT']=}")
            fcst_fn_tmpl = Template(vxcfg["FCST_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]).substitute(subvars)
        elif "ASNOW" in met_filedir_name:
            if do_ens:
                obs_in_dir = Path(exptdir, cdate, "obs", "metprd", "PcpCombine_obs")
                fcst_in_dir = Path(exptdir, cdate, ensmem, "metprd", "PcpCombine_fcst")
            else:
                obs_in_dir = Path(exptdir, cdate, "metprd", "PcpCombine_obs")
                fcst_in_dir = Path(exptdir, cdate, "metprd", "PcpCombine_fcst")
            obs_in_fn_template = Path(
                Template(
                    vxcfg["OBS_NOHRSC_ASNOW_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]
                ).substitute(subvars)
            )
            fcst_fn_tmpl = Path(
                Template(vxcfg["FCST_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]).substitute(subvars)
            )
        elif met_filedir_name == "REFC":
            obs_in_dir = obs_dir
            fcst_in_dir = vxcfg["VX_FCST_INPUT_BASEDIR"]
            obs_in_fn_template = vxcfg["OBS_MRMS_FN_TEMPLATES"][1]
            fcst_fn_tmpl = Template(vxcfg["FCST_FN_TEMPLATE"][ensmem_index]).substitute(subvars)
        elif met_filedir_name == "RETOP":
            obs_in_dir = obs_dir
            fcst_in_dir = vxcfg["VX_FCST_INPUT_BASEDIR"]
            obs_in_fn_template = vxcfg["OBS_MRMS_FN_TEMPLATES"][3]
            fcst_fn_tmpl = Template(vxcfg["FCST_FN_TEMPLATE"][ensmem_index]).substitute(subvars)
        else:
            raise ValueError(f"Invalid OBTYPE for GridStat: {obtype}")

    elif geom == "point":
        metplus_tool_name = "point_stat"
        metplus_tool_camel_case = "PointStat"
        if obtype == "NDAS":
            obs_in_dir = Path(exptdir, "metprd", "Pb2nc_obs")
            fcst_in_dir = vxcfg["VX_FCST_INPUT_BASEDIR"]
            obs_in_fn_template = vxcfg["OBS_NDAS_SFCandUPA_FN_TEMPLATE_PB2NC_OUTPUT"]
            fcst_fn_tmpl = Template(vxcfg["FCST_FN_TEMPLATE"][ensmem_index]).substitute(subvars)
        elif obtype == "AERONET":
            #AERONET format has slightly different names for different tasks
            met_filedir_name = "AERONET_AOD"
            obs_in_dir = Path(exptdir, "metprd", "Ascii2nc_obs")
            fcst_in_dir = vxcfg["VX_FCST_INPUT_BASEDIR"]
            obs_in_fn_template = vxcfg["OBS_AERONET_FN_TEMPLATE_ASCII2NC_OUTPUT"]
            fcst_fn_tmpl = Template(vxcfg["FCST_FN_TEMPLATE"][ensmem_index]).substitute(subvars)
        elif obtype == "AIRNOW":
            # AIRNOW format has slightly different names for different tasks, and also differs
            # based on ob source
            if vxcfg["AIRNOW_INPUT_FORMAT"] == "airnowhourly":
                met_filedir_name = "AIRNOW_HOURLY"
            elif vxcfg["AIRNOW_INPUT_FORMAT"] == "airnowhourlyaqobs":
                met_filedir_name = "AIRNOW_HOURLY_AQOBS"
            else:
                raise ValueError(f"Invalid AIRNOW_INPUT_FORMAT: {vxcfg['AIRNOW_INPUT_FORMAT']}")
            accum_hh=1
            obs_in_dir = Path(exptdir, "metprd", "Ascii2nc_obs")
            if do_ens:
                fcst_in_dir = Path(exptdir, cdate, ensmem, "metprd", "PcpCombine_fcst")
            else:
                fcst_in_dir = Path(exptdir, cdate, "metprd", "PcpCombine_fcst")
            obs_in_fn_template = vxcfg["OBS_AIRNOW_FN_TEMPLATE_ASCII2NC_OUTPUT"]
            fcst_fn_tmpl = Path(
                Template(vxcfg["FCST_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]).substitute(subvars)
            )
        else:
            raise ValueError(f"Invalid OBTYPE for PointStat: {obtype}")
    else:
        raise ValueError(f"Invalid parameters:\n{obtype=}\n{field_group=}\n{accum_hh=}")
    lgr.debug(f"{fcst_fn_tmpl=}")

    # Need to load gridstat or pointstat config section depending on what we're running
    taskcfg = cfg[metplus_tool_camel_case.lower()]

    if do_ens:
        output_dir=Path(exptdir, cdate, ensmem, "metprd", metplus_tool_camel_case)
        staging_dir=Path(exptdir, cdate, ensmem, "stage", met_filedir_name)
    else:
        output_dir=Path(exptdir, cdate, "metprd", metplus_tool_camel_case)
        staging_dir=Path(exptdir, cdate, "stage", met_filedir_name)

    # Make sure the MET/METplus output directory(ies) exists.
    os.makedirs(output_dir, exist_ok=True)

    # Set the lead hours for which to run the MET/METplus tool.  This is done by starting with the
    # the full list of lead hours for which we expect to find forecast output, then removing any
    # hours for which there is no corresponding observation data.

    if obtype in ["CCPA", "NOHRSC"]:
        vx_intvl = vx_hr_start = accum_hh
    else:
        vx_intvl = vxcfg["VX_FCST_OUTPUT_INTVL_HRS"]
        vx_hr_start = 0

    lgr.debug(f"set_leadhrs({cdate},{vx_hr_start},{cfg['workflow']['FCST_LEN_HRS']},{vx_intvl},"\
                 f"{obs_in_dir},{time_lag},{obs_in_fn_template},"\
                 f"{vxcfg['NUM_MISSING_OBS_FILES_MAX']})")
    vx_leadhr_list = set_leadhrs(cdate,vx_hr_start,cfg['workflow']['FCST_LEN_HRS'],vx_intvl,
                                 obs_in_dir,time_lag,str(obs_in_fn_template),
                                 vxcfg['NUM_MISSING_OBS_FILES_MAX'])

    if not vx_leadhr_list:
        raise RuntimeError(f"Call to set_leadhrs({cdate},{vx_hr_start},"\
                           f"{cfg['workflow']['FCST_LEN_HRS']},{vx_intvl},{obs_in_dir},"\
                           f"{time_lag},{obs_in_fn_template},"\
                           f"{vxcfg['NUM_MISSING_OBS_FILES_MAX']})\n"\
                            "returned an empty list.")

    vx_mask_files=[]
    if vxcfg["VX_MASK"]:
        for mask in vxcfg["VX_MASK"]:
            if os.path.isfile(maskfile:=f"{cfg['user']['METPLUS_CONF']}/{mask}.poly"):
                vx_mask_files.append(maskfile)
            else:
                vx_mask_files.append(f"{os.environ['MET_INSTALL_DIR']}/share/met/poly/{mask}.poly")

    # Set the names of the template METplus configuration file, the resulting rendered conf file,
    # and the METplus log file

    metplus_config_tmpl_fn="GridStat_or_PointStat.conf"
    metplus_config_fn=f"{metplus_tool_camel_case}_{met_filedir_name}_{field_group}_{ensmem}.conf.0"
    metplus_log_fn=f"metplus.log.{metplus_config_fn[:-7]}_{cdate}.0"

    # If user provided a fields: section for this task, use the thresholds defined there. Otherwise,
    # use the top-level fields: section
    vx_config_dict = cfg.get("fields")
    if taskcfg.get("fields"):
        vx_config_dict = taskcfg.get("fields")

    # Define variables that appear in the jinja template, add to existing settings dict.
    settings = {
               'metplus_tool_name': metplus_tool_name,
               'MetplusToolName': metplus_tool_camel_case,
               'METPLUS_TOOL_NAME': metplus_tool_name.upper(),
               'metplus_verbosity_level': vxcfg['METPLUS_VERBOSITY_LEVEL'],
               # Date and forecast hour information.
               'cdate': cdate,
               'vx_leadhr_list': ', '.join(map(str,vx_leadhr_list)),
               # Input and output directory/file information.
               'metplus_config_fn': metplus_config_fn,
               'metplus_log_fn': metplus_log_fn,
               'obs_input_dir': obs_in_dir,
               'obs_input_fn_template': obs_in_fn_template,
               'fcst_input_dir': fcst_in_dir,
               'fcst_input_fn_template': fcst_fn_tmpl,
               'output_dir': output_dir,
               'staging_dir': staging_dir,
               'vx_fcst_model_name': vxcfg['VX_FCST_MODEL_NAME'],
               # Ensemble and member-specific information.
               'ensmem_name': ensmem,
               'time_lag': time_lag,
               # Field information.
               'fieldname_in_obs_input': obs_in_dir,
               'fieldname_in_fcst_input': fcst_in_dir,
               'fieldname_in_met_output': met_out_name,
               'fieldname_in_met_filedir_names': met_filedir_name,
               'obtype': obtype,
               'accum_hh': f"{accum_hh:02}",
               'accum_no_pad': accum_hh,
               'metplus_templates_dir': cfg['user']['METPLUS_CONF'],
               'input_field_group': field_group,
               'input_level_fcst': fcst_level,
               'input_thresh_fcst': fcst_thresh,
               # Verification mask settings
               'vx_mask': ', '.join(vx_mask_files),
               # Rest of settings from yaml file
               'vx_config_dict': vx_config_dict
               }

    numprocs = int(cfg[metplus_tool_camel_case.lower()]["TASKS"])

    conf_files = render_metplus_confs(cfg,settings,metplus_config_tmpl_fn,vx_leadhr_list,numprocs)
    lgr.debug(f"{conf_files=}")

    lgr.info(f"Running {metplus_tool_camel_case} with METplus with {numprocs} tasks")
    mpargs = []
    for config_fn in conf_files:
        mpargs.append( (os.path.join(cfg['user']['METPLUS_CONF'], "common.conf"),config_fn) )
    # Call run_metplus function for as many processors as specified
        lgr.debug(f"{mpargs=}")
    with Pool(processes=numprocs) as pool:
        pool.starmap(run_metplus,mpargs)

    lgr.info(f"{metplus_tool_camel_case} completed successfully.")


def run_metplus(common_config,config_fn):
    """Calls the run_metplus script as a subprocess. If TASKS > 1 and vx_leadhr_list > 1,
    calls in with starmap for the number of tasks specified."""

    # Run METplus
    metplus_path = os.environ["METPLUS_ROOT"]
    subprocess.run([
        f"{metplus_path}/ush/run_metplus.py",
        "-c", common_config,
        "-c", config_fn
    ], check=True)


if __name__ == "__main__":
    #Parse arguments
    parser = argparse.ArgumentParser(
                     description="exscript for running METplus GridStat or PointStat tasks"\
                     "for deterministic verification\n")

    parser.add_argument('--accum_hh', default=1,type=int,
           help='Accumulation hours for this observation type')
    parser.add_argument('--config', default='config.yaml',type=str,
           help='Name of experiment config file in YAML format')
    parser.add_argument('--cycle_date', required=True, type=str,
           help='Eight-digit cycle date (YYMMDDHH)')
    parser.add_argument('--ensmem_index', required=True, type=int,
           help='The index for this ensemble member (0 for deterministic)')
    parser.add_argument('--field_group', required=True, type=str,
           help='Group of fields for this verification task (e.g. APCP, REFC, SFC, etc.)')
    parser.add_argument('--fcst_level', required=True, type=str,
           help='The "level" of the observation type as expected by MET (e.g. L0, A03, etc.)')
    parser.add_argument('--fcst_thresh', required=True, type=str,
           help='Set of forecast thresholds to verify against. Valid options are "all" and "none".')
    parser.add_argument('--obtype', required=True, type=str,
           help='Observation type for this verification task (e.g. NOHRSC, CCPA, NDAS, etc.)')
    parser.add_argument('--obs_dir', required=True, type=str,
           help='Observation directory for this obtype')
    parser.add_argument('-v', '--verbose', action='store_true',
           help='Script will be run in verbose mode')
    args = parser.parse_args()

    setup_logging(debug=args.verbose)

    logging.debug(f"{os.environ['METPLUS_ROOT']=}")

    gridstat_or_pointstat(args.config,args.cycle_date,args.obs_dir,args.field_group,args.obtype,
         args.accum_hh,args.ensmem_index,args.fcst_level,args.fcst_thresh)
