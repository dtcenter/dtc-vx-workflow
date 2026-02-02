#!/usr/bin/env python3
"""
Converted from scripts/ascii2nc_obs.sh
"""

import argparse
import os
import logging
import subprocess
from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

sys.path.insert(1, os.environ["USHdir"])

from python_utils import source_yaml,setup_logging
from eval_metplus_timestr_tmpl import eval_metplus_timestr_tmpl
from python_utils.metplus_conf_utils import render_metplus_confs
from set_leadhrs import set_leadhrs
from set_vx_params import set_vx_params

# ------------------------------------------------------------------
# Core functions ----------------------------------------------------
# ------------------------------------------------------------------

def main(config_file,cdate,obtype):
    logger = logging.getLogger(__name__)
    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    cfg = set_leadhrs(cfg)
    vxcfg = cfg["verification"]


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

    conf_file = render_metplus_confs(cfg,settings,"Ascii2nc_obs.conf",vx_leadhr_list,1)
    lgr.debug(f"{conf_file=}")

    lgr.info(f"Running {MetplusToolName} with METplus")
    run_metplus(os.path.join(cfg['user']['METPLUS_CONF'], "common.conf"),config_fn)

    lgr.info(f"Making completion flag file for {obtype}, cycle {cdate}")
    create_flag_file(cfg, obtype, cdate)
    lgr.info(f"{MetplusToolName} completed successfully.")


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
    pargs = parser.parse_args()

    setup_logging(debug=pargs.verbose)

main(pargs.config)
