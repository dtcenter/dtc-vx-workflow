# pylint: disable=logging-fstring-interpolation
"""
This is a python wrapper that sets up and executes the METplus *RegridDataPlane* verification task
for interpolating sparse observations onto a forecast grid
        
The script is intended to be called from jobs/REGRIDDATAPLANE.sh.
"""
import argparse
import logging
import os

from multiprocessing import Pool
from pathlib import Path
from string import Template

import uwtools.api.config as uwconfig

from python_utils import setup_logging,render_metplus_confs, run_metplus
from set_leadhrs import set_leadhrs

def regrid_data_plane(config_file,cdate,field_group,obtype):
    # pylint: disable=too-many-locals
    """Execute a METplus RegridDataPlane verification task.

    Parameters
    ----------
    config_file : str
        Path to the experiment YAML configuration file.
    cdate : str
        Eight‑digit cycle date in ``YYYYMMDDHH`` format.
    field_group : str
        Group of fields to verify (e.g., APCP, REFC, SFC).
    obtype : str
        Observation type for this verification task (currently only ``GOESAOD`` is supported).

    Returns
    -------
    None
        The function runs METplus as a side effect and exits when all tasks finish.

    Notes
    -----
    * Reads the experiment configuration and pulls verification settings.
    * Determines valid lead hours with `set_leadhrs`. Raises RuntimeError if the list is empty.
    * Generates a METplus configuration file for each lead hour using `render_metplus_confs`.
    * Executes `run_metplus` for each config file via a `multiprocessing.Pool` of 
      `regriddataplane: TASKS` workers.
    * A METplus log file is written for each parallel task.
    """
    lgr = logging.getLogger(__name__)

    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    # Set some aliases
    vxcfg = cfg["verification"]
    rdpcfg = cfg['regriddataplane']

    # Make a dictionary of variables that may need to be substituted; these will be used to replace
    # bash-like variables in some strings. This is needed to maintain some functionality while we
    # still have a mix of bash and python exscripts.
    subvars = {
            "time_lag": 0,
              }

    # Set paths and file templates for input to and output from the MET/
    # METplus tool to be run as well as other file/directory parameters.

    exptdir=vxcfg["VX_OUTPUT_BASEDIR"]
    metplus_tool_camel_case = "RegridDataPlane"
    if obtype == "GOESAOD":
        obs_in_dir = Path(exptdir, cdate, "metprd", "Point2Grid")
        obs_in_fn_template = vxcfg["OBS_GOES_AOD_FN_TEMPLATE_POINT2GRID_OUTPUT"]
        output_fn_template = f'regrid_{vxcfg["OBS_GOES_AOD_FN_TEMPLATE_POINT2GRID_OUTPUT"]}'
        # Get the list of all the times in the current day at which to retrieve obs.
    else:
        raise ValueError(f"Invalid OBTYPE for {metplus_tool_camel_case}: {obtype}")

    # Check that basic input directories exist:
    lgr.info(f"{obs_in_dir=}")
    if not Path(obs_in_dir).is_dir():
        raise FileNotFoundError(f"OBS_DIR does not exist or is not a directory:\n{obs_in_dir=}")

    #RegridDataPlane does not honor "time lag" shifts, so remove from template
    fcst_fn_template=Path(
                     vxcfg["VX_FCST_INPUT_BASEDIR"],
                     Template(vxcfg["FCST_SUBDIR_TEMPLATE"]).substitute(subvars),
                     Template(vxcfg["FCST_FN_TEMPLATE"]).substitute(subvars)
                     )
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

    # Set the names of the template METplus configuration file, the resulting rendered conf file,
    # and the METplus log file
    metplus_config_tmpl_fn="RegridDataPlane.conf"
    metplus_config_fn=f"{metplus_tool_camel_case}_{field_group}.conf.0"
    metplus_log_fn=f"metplus.log.{metplus_config_fn[:-7]}_{cdate}.0"

    # Define variables that appear in the jinja template, add to existing settings dict.
    settings = {
               'metplus_verbosity_level': vxcfg['METPLUS_VERBOSITY_LEVEL'],
               # Date and forecast hour information.
               'cdate': cdate,
               'vx_leadhr_list': ', '.join(map(str,vx_leadhr_list)),
               # Interpolation information
               'regrid_method': rdpcfg['REGRID_METHOD'],
               'gaussian_dx': rdpcfg['GAUSSIAN_DX'],
               'gaussian_radius': rdpcfg['GAUSSIAN_RADIUS'],
               # Input and output directory/file information.
               'metplus_config_fn': metplus_config_fn,
               'metplus_log_fn': metplus_log_fn,
               'obs_input_dir': obs_in_dir,
               'obs_input_fn_template': obs_in_fn_template,
               'output_dir': output_dir,
               'output_fn_template': output_fn_template,
               'fcst_fn_template': fcst_fn_template,
               # Field information.
               'obtype': obtype,
               'level': 'L550'
               }

    numprocs=rdpcfg['TASKS']
    conf_files = render_metplus_confs(cfg,settings,metplus_config_tmpl_fn,vx_leadhr_list,numprocs)
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


if __name__ == "__main__":
    #Parse arguments
    parser = argparse.ArgumentParser(
                     description="exscript for running METplus RegridDataPlane tasks"\
                     "for deterministic verification\n")

    parser.add_argument(
        "--config",
        default="config.yaml",
        type=str,
        help="Name of experiment config file in YAML format"
    )
    parser.add_argument(
        "--cycle_date",
        required=True,
        type=str,
        help="Eight-digit cycle date (YYMMDDHH)",
    )
    parser.add_argument(
        "--field_group",
        required=True,
        type=str,
        help="Group of fields for this verification task (e.g. APCP, REFC, SFC, etc.)",
    )
    parser.add_argument(
        "--obtype",
        required=True,
        type=str,
        help="Observation type for this verification task (e.g. NOHRSC, CCPA, NDAS, etc.)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Script will be run in verbose mode",
    )
    pargs = parser.parse_args()

    setup_logging(debug=pargs.verbose)

    logging.debug(f"{os.environ['METPLUS_ROOT']=}")

    regrid_data_plane(pargs.config,pargs.cycle_date,pargs.field_group,pargs.obtype)
