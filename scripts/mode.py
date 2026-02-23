# pylint: disable=logging-fstring-interpolation
"""
This is a python wrapper that sets up and executes the METplus *MODE* verification task for
deterministic verification.

The script is intended to be called from jobs/MODE.sh.
"""
import argparse
import logging
import os
import subprocess

from multiprocessing import Pool
from pathlib import Path
from string import Template

import uwtools.api.config as uwconfig

from python_utils import setup_logging, render_metplus_confs, make_var_lists
from set_leadhrs import set_leadhrs

def mode(config_file,cdate,field_group,obtype):
    # pylint: disable=too-many-locals
    """
    Execute a METplus MODE verification task.

    Parameters
    ----------
    config_file : str
        Path to the experiment YAML configuration file.
    cdate : str
        Eight‑digit cycle date in ``YYYYMMDDHH`` format.
    field_group : str
        Group of fields to verify (e.g., ``APCP``, ``REFC``, ``SFC``).
    obtype : str
        Observation type for this verification task (e.g., ``GOESAOD``).

    Returns
    -------
    None
        The function runs METplus, potentially in parallel with multiprocessing depending on user
        settings, and exits when all tasks finish.

    Notes
    -----
    * Reads the experiment configuration and pulls-verification and MODE-specific settings from the
      YAML files.
    * For the current implementation only ``GOESAOD`` is supported; the function sets up observation
      and forecast directories, and constructs templates for input files.
    * A list of valid lead hours is computed with `set_leadhrs`.  If the list is empty a
      `RuntimeError` is raised.
    * Mask files for verification over specific regions are located from the METplus configuration
      directory or the MET install directory.
    * Variable names for forecast and observation data are built with `make_var_lists` based on the
      field group.
    * A Jinja configuration template (``MODE.conf``) is rendered into a METplus conf file for each
      lead hour, then each rendered file is run with `run_metplus` using a `multiprocessing.Pool`
      of `mode: TASKS` workers.
    * A METplus log file is written for each parallel task.

    """
    lgr = logging.getLogger(__name__)

    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    # Set some aliases
    vxcfg = cfg["verification"]
    modecfg = cfg["mode"]

    # Make a dictionary of variables that may need to be substituted; these will be used to replace
    # bash-like variables in some strings. This is needed to maintain some functionality while we
    # still have a mix of bash and python exscripts.
    subvars = {
            "time_lag": 0,
              }

    # Set paths and file templates for input to and output from the MET/
    # METplus tool to be run as well as other file/directory parameters.

    exptdir=vxcfg["VX_OUTPUT_BASEDIR"]
    metplus_tool_camel_case = "MODE"
    if obtype == "GOESAOD":
        obs_in_dir = Path(exptdir, cdate, "metprd", "RegridDataPlane")
        obs_in_fn_template = f'regrid_{vxcfg["OBS_GOES_AOD_FN_TEMPLATE_POINT2GRID_OUTPUT"]}'
        fcst_in_dir = vxcfg["VX_FCST_INPUT_BASEDIR"]
        fcst_in_fn_template = Path(Template(vxcfg["FCST_SUBDIR_TEMPLATE"]).substitute(subvars),
                                   Template(vxcfg["FCST_FN_TEMPLATE"]).substitute(subvars))
        # Get the list of all the times in the current day at which to retrieve obs.
    else:
        raise ValueError(f"Invalid OBTYPE for {metplus_tool_camel_case}: {obtype}")

    output_dir=Path(exptdir, cdate, "metprd", metplus_tool_camel_case)
    # Make sure the MET/METplus output directory(ies) exists.
    os.makedirs(output_dir, exist_ok=True)

    # Set the lead hours for which to run the MET/METplus tool.  This is done by starting with the
    # the full list of lead hours for which we expect to find forecast output, then removing any
    # hours for which there is no corresponding observation data.

    vx_intvl = vxcfg["VX_FCST_OUTPUT_INTVL_HRS"]
    vx_hr_start = 0

    lgr.debug(slh_string:=f"set_leadhrs({cdate},{vx_hr_start},{cfg['workflow']['FCST_LEN_HRS']},"\
                 f"{vx_intvl},{obs_in_dir},0,{obs_in_fn_template},"\
                 f"{vxcfg['NUM_MISSING_OBS_FILES_MAX']})")
    vx_leadhr_list = set_leadhrs(cdate,vx_hr_start,cfg['workflow']['FCST_LEN_HRS'],vx_intvl,
                                 obs_in_dir,0,str(obs_in_fn_template),
                                 vxcfg['NUM_MISSING_OBS_FILES_MAX'])

    if not vx_leadhr_list:
        raise RuntimeError(f"Call to {slh_string}\nreturned an empty list.")

    vx_mask_files=[]
    if vxcfg["VX_MASK"]:
        for mask in vxcfg["VX_MASK"]:
            if os.path.isfile(maskfile:=f"{cfg['user']['METPLUS_CONF']}/{mask}.poly"):
                vx_mask_files.append(maskfile)
            else:
                vx_mask_files.append(f"{os.environ['MET_INSTALL_DIR']}/share/met/poly/{mask}.poly")

    # Set the names of the template METplus configuration file, the resulting rendered conf file,
    # and the METplus log file
    metplus_config_tmpl_fn="MODE.conf"
    metplus_config_fn=f"{metplus_tool_camel_case}_{field_group}.conf.0"
    metplus_log_fn=f"metplus.log.{metplus_config_fn[:-7]}_{cdate}.0"

    # Load YAML file containing configuration for deterministic verification
    vx_config_dict = uwconfig.get_yaml_config(config=f"{cfg['user']['METPLUS_CONF']}/"\
                                                     f"{vxcfg['VX_CONFIG_DET_FN']}")

    # Create the entries for forecast and variable names to pass to METplus conf file. This logic
    # is overkill for now but serves as a template for how this could be done in
    # gridstat_or_pointstat.py

    fcst_var_list,obs_var_list=make_var_lists(vx_config_dict,field_group)

    # Define variables that appear in the jinja template, add to existing settings dict.
    settings = {
               'metplus_verbosity_level': vxcfg['METPLUS_VERBOSITY_LEVEL'],
               # Date and forecast hour information.
               'cdate': cdate,
               'vx_leadhr_list': ', '.join(map(str,vx_leadhr_list)),
               # Timing window information
               'obs_window_begin': 0,
               'obs_window_end': 0,
               # Interpolation information; this should only be FORCE if forecast and ob grids are
               # identical, as they are for GOES since we already did an interpolation
               'regrid_method': 'FORCE',
               # Input and output directory/file information.
               'metplus_config_fn': metplus_config_fn,
               'metplus_log_fn': metplus_log_fn,
               'obs_input_dir': obs_in_dir,
               'obs_input_fn_template': obs_in_fn_template,
               'output_dir': output_dir,
               'output_fn_template': modecfg["OUTPUT_TEMPLATE"],
               'fcst_input_dir': fcst_in_dir,
               'fcst_input_fn_template': fcst_in_fn_template,
               'vx_fcst_model_name': vxcfg['VX_FCST_MODEL_NAME'],
               # Variable lists
               'fcst_var_list': fcst_var_list,
               'obs_var_list': obs_var_list,
               # Field information.
               'obtype': obtype,
               # Verification mask settings
               'vx_mask': ', '.join(vx_mask_files),
               # MODE object generation settings
               'conv_radius': modecfg["CONV_RADIUS"],
               'conv_thresh': modecfg["CONV_THRESH"],
               'merge_thresh': modecfg["MERGE_THRESH"],
               'merge_flag': modecfg["MERGE_FLAG"],
               }

    numprocs=modecfg['TASKS']
    conf_files = render_metplus_confs(cfg,settings,metplus_config_tmpl_fn,vx_leadhr_list,
                                      len(vx_leadhr_list))
    lgr.debug(f"{conf_files=}")

    lgr.info(f"Running {metplus_tool_camel_case} with METplus with {numprocs} tasks")
    args = []
    for config_fn in conf_files:
        args.append( (os.path.join(cfg['user']['METPLUS_CONF'], "common.conf"),config_fn) )
    # Call run_metplus function for as many processors as specified
        lgr.debug(f"{args=}")
    with Pool(processes=numprocs) as pool:
        pool.starmap(run_metplus,args)

    lgr.info(f"{metplus_tool_camel_case} completed successfully.")


def run_metplus(common_config,config_fn):
    """Calls the run_metplus script as a subprocess."""
    logger = logging.getLogger(__name__)

    # Run METplus
    metplus_path = os.environ["METPLUS_ROOT"]
    logger.debug(f"{common_config=}")
    logger.debug(f"{config_fn=}")
    logger.debug(f"{metplus_path=}")
    subprocess.run([
        f"{metplus_path}/ush/run_metplus.py",
        "-c", common_config,
        "-c", config_fn
    ], check=True)


if __name__ == "__main__":
    #Parse arguments
    parser = argparse.ArgumentParser(
                     description="exscript for running METplus MODE tasks"\
                     "for deterministic verification\n")

    parser.add_argument(
        "--config", default="config.yaml", type=str,
        help="Name of experiment config file in YAML format",
    )
    parser.add_argument(
        "--cycle_date", required=True, type=str,
        help="Eight-digit cycle date (YYMMDDHH)",
    )
    parser.add_argument(
        "--field_group", required=True, type=str,
        help="Group of fields for this verification task (e.g. APCP, REFC, SFC, etc.)",
    )
    parser.add_argument(
        "--obtype", required=True, type=str,
        help="Observation type for this verification task (e.g. NOHRSC, CCPA, NDAS, etc.)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Script will be run in verbose mode",
    )
    pargs = parser.parse_args()

    setup_logging(debug=pargs.verbose)

    # Retrieve needed args from environment; should pass these explicitly in the future
    logging.info(f"{os.environ['METPLUS_ROOT']=}")

    mode(pargs.config,pargs.cycle_date,pargs.field_group,pargs.obtype)
