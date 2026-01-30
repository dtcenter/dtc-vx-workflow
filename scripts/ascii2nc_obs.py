#!/usr/bin/env python3
"""
Converted from scripts/ascii2nc_obs.sh
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# ------------------------------------------------------------------
# USHdir helpers ----------------------------------------------------
# ------------------------------------------------------------------
sys.path.insert(1, os.environ["USHdir"])

from source_util_funcs import (
    print_info_msg,
    print_err_msg_exit,
    get_metplus_tool_name,
    source_yaml,
)
from eval_metplus_timestr_tmpl import eval_metplus_timestr_tmpl
from python_utils.metplus_conf_utils import render_metplus_confs
from set_leadhrs import set_leadhrs
from set_vx_params import set_vx_params

# ------------------------------------------------------------------
# Core functions ----------------------------------------------------
# ------------------------------------------------------------------

def load_yaml_config(path: Path):
    cfg = source_yaml(path)
    return cfg


def get_leadhr_list(cfg, obtype, yyyymmdd_task: str, hh: str) -> str:
    obs_retrieve_times = cfg["point2grid"]["OBS_RETRIEVE_TIMES_{}".format(obtype)][yyyymmdd_task]
    leadhr_list = []
    num_missing_files = 0
    for yyyymmddhh in obs_retrieve_times:
        yyyymmdd = yyyymmddhh[:8]
        hh_str = yyyymmddhh[8:10]
        sec_ref_task = int(datetime.strptime(yyyymmdd_task, "%Y%m%d%H").timestamp())
        sec_now = int(datetime.strptime(f"{yyyymmdd} {hh_str} hours", "%Y%m%d %H hours").timestamp())
        lhr = (sec_now - sec_ref_task) // 3600
        fp = eval_metplus_timestr_tmpl(
            init_time=f"{yyyymmdd_task}00",
            lhr=lhr,
            fn_template=f"{cfg['verification']['OBS_DIR']}/$OBTYPE_INPUT_FN_TEMPLATE",
        )
        if Path(fp).is_file():
            leadhr_list.append(f"{int(hh_str, 10)}")
        else:
            num_missing_files += 1
    if num_missing_files > cfg["point2grid"]["NUM_MISSING_OBS_FILES_MAX"]:
        print_err_msg_exit(
            f"The number of missing {obtype} obs files ({num_missing_files}) "
            f"is greater than the maximum allowed "
            f"({cfg['point2grid']['NUM_MISSING_OBS_FILES_MAX']})"
        )
    if not leadhr_list:
        print_err_msg_exit("No valid forecast hours found.")
    return ",".join(leadhr_list)


def render_template(cfg, obtype, cdate: str, leadhr_list: str):
    from jinja2 import Environment, FileSystemLoader
    tmpl_dir = Path(cfg["user"]["METPLUS_CONF"])
    env = Environment(loader=FileSystemLoader(tmpl_dir))
    tmpl = env.get_template(f"{cfg['point2grid']['METPLUSTOOLNAME']}_obs.conf")
    rendered = tmpl.render(
        metplus_tool_name=cfg["point2grid"]["METPLUSTOOLNAME"],
        MetplusToolName=cfg["point2grid"]["METPLUSTOOLNAME"],
        METPLUS_TOOL_NAME=cfg["point2grid"]["METPLUSTOOLNAME"].upper(),
        metplus_verbosity_level=cfg["point2grid"]["METPLUS_VERBOSITY_LEVEL"],
        cdate=cdate,
        fhr_list=leadhr_list,
        metplus_config_fn="",
        metplus_log_fn="",
        obs_input_dir=cfg["verification"]["OBS_DIR"],
        obs_input_fn_template=cfg["point2grid"]["OBS_INPUT_FN_TEMPLATE"],
        fcst_input_dir="",
        fcst_input_fn_template="",
        output_dir=cfg["verification"]["VX_OUTPUT_BASEDIR"],
        output_fn_template="",
        staging_dir="",
        vx_fcst_model_name="",
        input_format=cfg["point2grid"]["ASCII2NC_INPUT_FORMAT"],
        num_ens_members=cfg["point2grid"]["NUM_ENS_MEMBERS"],
        ensmem_name="",
        time_lag="",
        obtype=obtype,
    )
    output_path = Path(cfg["verification"]["VX_OUTPUT_BASEDIR"]) / "metprd" / cfg["point2grid"]["METPLUSTOOLNAME"] / f"{cdate}/metplus.log.{cdate}.0"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered)
    return output_path


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
    args = parser.parse_args()

    cfg = load_yaml_config(Path(args.config))
    cfg = set_vx_params(cfg)
    cfg = set_leadhrs(cfg)

    yyyymmdd_task = args.cycle_date[:6]
    hh = args.cycle_date[6:8]
    cdate = args.cycle_date

    leadhr_list = get_leadhr_list(cfg, args.obtype, yyyymmdd_task, hh)
    config_fp = render_template(cfg, args.obtype, cdate, leadhr_list)
    run_metplus(cfg, config_fp)
    create_flag_file(cfg, args.obtype, yyyymmdd_task)
    print_info_msg("METplus ASCII2NC conversion completed successfully.")
