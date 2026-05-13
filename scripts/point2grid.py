# pylint: disable=logging-fstring-interpolation
"""
This is a python wrapper that sets up and executes the METplus *Point2Grid* verification task for
converting point observations onto the same grid as a provided forecast file.
        
The script is intended to be called from jobs/POINT2GRID.sh.
"""
import argparse
import logging
import os

from multiprocessing import Pool
from pathlib import Path
from string import Template

import uwtools.api.config as uwconfig

from python_utils import render_metplus_confs, run_metplus, setup_logging
from set_leadhrs import set_leadhrs

def point2grid(config_file,cdate,obs_dir,field_group,obtype,fcst_level,fcst_thresh):
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    """Execute the METplus Point2Grid task.

    Parameters
    ----------
    config_file : str
        Path to the experiment YAML configuration file.
    cdate : str
        Eight‑digit cycle date in ``YYYYMMDDHH`` format.
    obs_dir : str
        Directory containing point observations for the selected ``obtype``.
    field_group : str
        Group of fields to verify (e.g., ``APCP``, ``REFC``, ``SFC``).
    obtype : str
        Observation type for this verification (currently only ``GOESAOD`` is supported).
    fcst_level : str
        Forecast level (e.g., ``L0`` or ``A03``) expected by MET.
    fcst_thresh : str
        Forecast threshold set to verify against; usually ``"all"`` or ``"none"``.

    Returns
    -------
    None
        The function runs METplus, potentially in parallel with multiprocessing depending on user
        settings, and exits when all tasks finish.

    Notes
    -----
    * Reads the experiment configuration and pulls verification settings.
    * Constructs observation, forecast, and output directories, and creates file templates for the
      Point2Grid run.
    * Determines valid lead hours with `set_leadhrs`.  If the list is empty a `RuntimeError` is
      raised.
    * Generates a configuration file from the Point2Grid.conf jinja template for each lead hour
      using `render_metplus_confs`
    * Executes :func:`run_metplus` for each rendered .conf file through a `multiprocessing.Pool` of
      ``vxcfg['VX_TASKS']`` workers.
    * A METplus log file is written for each parallel task.
    """
    lgr = logging.getLogger(__name__)

    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    # Set some aliases
    vxcfg = cfg["verification"]

    # Check that basic input directories exist:
    lgr.info(f"{obs_dir=}")
    if not Path(obs_dir).is_dir():
        raise FileNotFoundError(f"OBS_DIR does not exist or is not a directory:\n{obs_dir=}")

    # Make a dictionary of variables that may need to be substituted; these will be used to replace
    # bash-like variables in some strings. This is needed to maintain some functionality while we
    # still have a mix of bash and python exscripts.
    subvars = {
            "time_lag": 0,
              }

    # Set paths and file templates for input to and output from the MET/
    # METplus tool to be run as well as other file/directory parameters.

    exptdir=vxcfg["VX_OUTPUT_BASEDIR"]
    metplus_tool_camel_case = "Point2Grid"
    if obtype == "GOESAOD":
        obs_in_dir = vxcfg["GOESAOD_OBS_DIR"]
        obs_in_fn_template = vxcfg["OBS_GOESAOD_FN_TEMPLATES"][1]
        adp_input_fn_template = Path(vxcfg["GOESADP_OBS_DIR"],vxcfg["OBS_GOESADP_FN_TEMPLATES"][1])
        output_fn_template = f'{vxcfg["OBS_GOES_AOD_FN_TEMPLATE_POINT2GRID_OUTPUT"]}'
        # Get the list of all the times in the current day at which to retrieve obs.
    else:
        raise ValueError(f"Invalid OBTYPE for {metplus_tool_camel_case}: {obtype}")

    #Point2Grid does not honor "time lag" shifts, so remove from template
    fcst_fn_template=Path(
                     vxcfg["VX_FCST_INPUT_BASEDIR"],
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
                 f"{vx_intvl},"\
                 f"{obs_in_dir},0,{obs_in_fn_template},{vxcfg['NUM_MISSING_OBS_FILES_MAX']})")
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
    metplus_config_tmpl_fn="Point2Grid.conf"
    metplus_config_fn=f"{metplus_tool_camel_case}_{field_group}.conf.0"
    metplus_log_fn=f"metplus.log.{metplus_config_fn[:-7]}_{cdate}.0"

    # Load YAML file containing configuration for deterministic verification
    vx_config_dict = uwconfig.get_yaml_config(config=f"{cfg['user']['METPLUS_CONF']}/"\
                                                     f"{vxcfg['VX_CONFIG_DET_FN']}")

    # Define variables that appear in the jinja template
    settings = {
               'metplus_verbosity_level': vxcfg['METPLUS_VERBOSITY_LEVEL'],
               # Date and forecast hour information.
               'cdate': cdate,
               'vx_leadhr_list': ', '.join(map(str,vx_leadhr_list)),
               # Interpolation information
               'regrid_method': cfg['point2grid']['REGRID_METHOD'],
               'goes_qc_flags': cfg['point2grid']['GOES_QC_FLAGS'],
               # Input and output directory/file information.
               'metplus_config_fn': metplus_config_fn,
               'metplus_log_fn': metplus_log_fn,
               'obs_input_dir': obs_in_dir,
               'obs_input_fn_template': obs_in_fn_template,
               'adp_input_fn_template': adp_input_fn_template,
               'output_dir': output_dir,
               'output_fn_template': output_fn_template,
               'fcst_fn_template': fcst_fn_template,
               # Field information.
               'obtype': obtype,
               'metplus_templates_dir': cfg['user']['METPLUS_CONF'],
               'input_field_group': field_group,
               'input_level_fcst': fcst_level,
               'input_thresh_fcst': fcst_thresh,
               # Rest of settings from yaml file
               'vx_config_dict': vx_config_dict
               }

    numprocs=vxcfg['VX_TASKS']
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
                     description="script for running METplus Point2Grid tasks"\
                     "for deterministic verification\n")

#    parser.add_argument('-c', '--config', default='config.yaml',
#                        help='Name of experiment config file in YAML format')
    parser.add_argument('--config', default='config.yaml',type=str,
           help='Name of experiment config file in YAML format')
    parser.add_argument('--cycle_date', required=True, type=str,
           help='Eight-digit cycle date (YYMMDDHH)')
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
    pargs = parser.parse_args()

    setup_logging(debug=pargs.verbose)

    # Retrieve needed args from environment; should pass these explicitly in the future
    logging.info(f"{os.environ['METPLUS_ROOT']=}")

    point2grid(pargs.config,pargs.cycle_date,pargs.obs_dir,pargs.field_group,pargs.obtype,
         pargs.fcst_level,pargs.fcst_thresh)
