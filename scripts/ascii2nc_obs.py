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

def main(config_file,cdate,obtype,field_group):
    MetplusToolName="Ascii2nc"
    lgr = logging.getLogger(__name__)
    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    cfg = set_leadhrs(cfg)
    vxcfg = cfg["verification"]


    output_dir=Path(exptdir, cdate, "metprd", "Ascii2nc_obs")
    # Make sure the MET/METplus output directory(ies) exists.
    os.makedirs(output_dir, exist_ok=True)

    if obtype == "AERONET":
        obs_in_dir = vxcfg["AERONET_OBS_DIR"]
        obs_in_fn_template = vxcfg["OBS_AERONET_FN_TEMPLATES"][1]
        output_fn_template = f'{vxcfg["OBS_AERONET_FN_TEMPLATE_ASCII2NC_OUTPUT"]}'
        input_format = aeronetv3
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

    lgr.debug(f"set_leadhrs({cdate},{vx_hr_start},{cfg['workflow']['FCST_LEN_HRS']},{vx_intvl},"\
                 f"{obs_in_dir},{time_lag},{obs_in_fn_template},"\
                 f"{vxcfg['NUM_MISSING_OBS_FILES_MAX']})")
    leadhr_list = set_leadhrs(cdate,vx_hr_start,cfg['workflow']['FCST_LEN_HRS'],vx_intvl,
                                 obs_in_dir,time_lag,str(obs_in_fn_template),
                                 vxcfg['NUM_MISSING_OBS_FILES_MAX']) 
    
    if not leadhr_list:
        raise RuntimeError(f"Call to set_leadhrs({cdate},{vx_hr_start},"\
                           f"{cfg['workflow']['FCST_LEN_HRS']},{vx_intvl},{obs_in_dir},"\
                           f"{time_lag},{obs_in_fn_template},"\
                           f"{vxcfg['NUM_MISSING_OBS_FILES_MAX']})\n"\
                            "returned an empty list.")

    # Set the names of the template METplus configuration file, the resulting rendered conf file,
    # and the METplus log file
    metplus_config_tmpl_fn="Point2Grid.conf"
    metplus_config_fn=f"{MetplusToolName}_{field_group}.conf.0"
    metplus_log_fn=f"metplus.log.{metplus_config_fn[:-7]}_{cdate}.0"

    # Define variables that appear in the jinja template, add to existing settings dict.
    settings = {
               'metplus_verbosity_level': vxcfg['METPLUS_VERBOSITY_LEVEL'],
               'METPLUS_TOOL_NAME': MetplusToolName.upper(),
               # Date and forecast hour information.
               'cdate': cdate,
               'leadhr_list': ', '.join(map(str,leadhr_list)),
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

    conf_file = render_metplus_confs(cfg,settings,"Ascii2nc_obs.conf",leadhr_list,1)
    lgr.debug(f"{conf_file=}")

    lgr.info(f"Running {MetplusToolName.upper()} with METplus")
    run_metplus(os.path.join(cfg['user']['METPLUS_CONF'], "common.conf"),conf_file)

    lgr.info(f"Making completion flag file for {obtype}, cycle {cdate}")
    create_flag_file(cfg, obtype, cdate)
    lgr.info(f"{MetplusToolName.upper()} completed successfully.")


def run_metplus(cfg, config_fp: Path):
    metplus_root = Path(os.environ["METPLUS_ROOT"])
    common_conf = Path(cfg["user"]["METPLUS_CONF"]) / "common.conf"
    subprocess.run(
        [
            str(metplus_root / "ush" / "run_metplus.py"),
            "-c",
            str(common_conf),
            "-c",
            str(config_fp),
        ],
        check=True,
    )


def create_flag_file(cfg, obtype: str, yyyymmdd: str):
    flag_dir = Path(cfg["verification"]["WFLOW_FLAG_FILES_DIR"])
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

    parser.add_argument('--field_group', required=True, type=str,
                        help='Group of fields for this verification task (e.g. APCP, REFC, SFC, etc.)')

    pargs = parser.parse_args()

    setup_logging(debug=pargs.verbose)

    main(pargs.config,pargs.cycle_date,pargs.obtype,pargs.field_group)
