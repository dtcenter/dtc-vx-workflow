#!/usr/bin/env python3
"""
Converted from scripts/ascii2nc_obs.sh
"""

import argparse
import os
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime

import uwtools.api.config as uwconfig

sys.path.insert(1, os.environ["USHdir"])

from python_utils import setup_logging,render_metplus_confs
from eval_metplus_timestr_tmpl import eval_metplus_timestr_tmpl
from set_leadhrs import set_leadhrs
from set_vx_params import set_vx_params

# ------------------------------------------------------------------
# Core functions ----------------------------------------------------
# ------------------------------------------------------------------

def main(config_file,cdate,obtype):
    MetplusToolName="Ascii2nc"
    lgr = logging.getLogger(__name__)
    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    vxcfg = cfg["verification"]


    output_dir=Path(vxcfg["VX_OUTPUT_BASEDIR"], "metprd", "Ascii2nc_obs")
    # Make sure the MET/METplus output directory(ies) exists.
    os.makedirs(output_dir, exist_ok=True)

    if obtype == "AERONET":
        obs_in_dir = vxcfg["AERONET_OBS_DIR"]
        obs_in_fn_template = vxcfg["OBS_AERONET_FN_TEMPLATES"][1]
        output_fn_template = f'{vxcfg["OBS_AERONET_FN_TEMPLATE_ASCII2NC_OUTPUT"]}'
        input_format = "aeronetv3"
    elif obtype == "AIRNOW":
        obs_in_dir = vxcfg["AIRNOW_OBS_DIR"]
        obs_in_fn_template = vxcfg["OBS_AIRNOW_FN_TEMPLATES"][1]
        output_fn_template = f'{vxcfg["OBS_AIRNOW_FN_TEMPLATE_ASCII2NC_OUTPUT"]}'
        input_format = vxcfg["AIRNOW_INPUT_FORMAT"]
    else:
        raise ValueError(f"Invalid OBTYPE for {MetplusToolName.upper()}: {obtype}")


    time_lag=0
    vx_intvl = vxcfg["VX_FCST_OUTPUT_INTVL_HRS"]
    vx_hr_start = 0

    lgr.debug(slh_string:=f"set_leadhrs({cdate},{vx_hr_start},{cfg['workflow']['FCST_LEN_HRS']},"\
                 f"{vx_intvl},{obs_in_dir},{time_lag},{obs_in_fn_template},"\
                 f"{vxcfg['NUM_MISSING_OBS_FILES_MAX']})")
    vx_leadhr_list = set_leadhrs(cdate,vx_hr_start,cfg['workflow']['FCST_LEN_HRS'],vx_intvl,
                                 obs_in_dir,time_lag,str(obs_in_fn_template),
                                 vxcfg['NUM_MISSING_OBS_FILES_MAX']) 
    
    if not vx_leadhr_list:
        raise RuntimeError(f"Call to {slh_string} returned an empty list.")

    # Set the names of the template METplus configuration file, the resulting rendered conf file,
    # and the METplus log file
    metplus_config_tmpl_fn="Point2Grid.conf"
    metplus_config_fn=f"{MetplusToolName}_{obtype}.conf.0"
    metplus_log_fn=f"metplus.log.{metplus_config_fn[:-7]}_{cdate}.0"

    # Define variables that appear in the jinja template, add to existing settings dict.
    settings = {
               'metplus_verbosity_level': vxcfg['METPLUS_VERBOSITY_LEVEL'],
               'METPLUS_TOOL_NAME': MetplusToolName.upper(),
               # Date and forecast hour information.
               'cdate': cdate,
               'vx_leadhr_list': ', '.join(map(str,vx_leadhr_list)),
               # Input and output directory/file information.
               'metplus_config_fn': metplus_config_fn,
               'metplus_log_fn': metplus_log_fn,
               'obs_input_dir': obs_in_dir,
               'obs_input_fn_template': obs_in_fn_template,
               'output_dir': output_dir, 
               'output_fn_template': output_fn_template,
               # Field information.
               'obtype': obtype,
               'input_format': input_format,
               }

    conf_file = render_metplus_confs(cfg,settings,"Ascii2nc_obs.conf",vx_leadhr_list,1)
    lgr.debug(f"{conf_file=}")

    lgr.info(f"Running {MetplusToolName.upper()} with METplus")
    run_metplus(os.path.join(cfg['user']['METPLUS_CONF'], "common.conf"),conf_file[0])

    lgr.info(f"Making completion flag file for {obtype}, cycle {cdate}")
    create_flag_file(cfg, obtype, cdate)
    lgr.info(f"{MetplusToolName.upper()} completed successfully.")


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


def create_flag_file(cfg, obtype: str, yyyymmdd: str):
    flag_dir = Path(cfg["workflow"]["WFLOW_FLAG_FILES_DIR"])
    flag_dir.mkdir(parents=True, exist_ok=True)
    flag_file = flag_dir / f"{obtype}_nc_obs_{yyyymmdd}_ready.txt"
    flag_file.touch()

# ------------------------------------------------------------------
# Main ---------------------------------------------------------------
# ------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ASCII→NetCDF conversion for observation files"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        type=str,
        help="YAML experiment configuration file",
    )
    parser.add_argument(
        "--cycle_date",
        required=True,
        type=str,
        help="Eight‑digit cycle date (YYMMDDHH)",
    )
    parser.add_argument(
        "--obtype",
        required=True,
        type=str,
        help="Observation type (e.g. AERONET, AIRNOW)",
    )

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Script will be run in verbose mode')

    pargs = parser.parse_args()

    setup_logging(debug=pargs.verbose)

    main(pargs.config,pargs.cycle_date,pargs.obtype)
