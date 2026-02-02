#!/usr/bin/env python3
"""
Converted from scripts/pb2nc_obs.sh
"""

import argparse
import os
import logging
import subprocess
from pathlib import Path

import uwtools.api.config as uwconfig

# Import utilities and helpers
from python_utils import setup_logging, render_metplus_confs
from eval_metplus_timestr_tmpl import eval_metplus_timestr_tmpl
from set_leadhrs import set_leadhrs
from set_vx_params import set_vx_params


def main(config_file: str, cycle_date: str, obtype: str, field_group: str, accum_hh: int, verbose: bool = False):
    """Main routine for PB2NC observation conversion.

    Parameters
    ----------
    config_file : str
        Path to the experiment configuration YAML.
    cycle_date : str
        Eight‑digit cycle date in ``YYMMDDHH`` format.
    obtype : str
        Observation type (e.g. ``NDAS``).
    field_group : str
        Field group for the observation type.
    accum_hh : int
        Accumulation hour.
    verbose : bool, optional
        Enable debug logging.
    """

    # Set up basic logger
    lgr = logging.getLogger(__name__)
    if verbose:
        setup_logging(debug=True)
    else:
        setup_logging(debug=False)

    # Load the YAML configuration
    cfg = uwconfig.get_yaml_config(config=config_file)
    vxcfg = cfg["verification"]

    # ---------------------------------------------------------------------
    # Determine observation and output directories and templates
    # ---------------------------------------------------------------------
    OBS_DIR = vxcfg["OBS_DIR"]
    OBS_NDAS_FN_TEMPLATES = vxcfg["OBS_NDAS_FN_TEMPLATES"]
    if len(OBS_NDAS_FN_TEMPLATES) < 2:
        raise ValueError("OBS_NDAS_FN_TEMPLATES must contain at least two templates.")
    OBS_INPUT_FN_TEMPLATE = OBS_NDAS_FN_TEMPLATES[1]
    OUTPUT_FN_TEMPLATE = vxcfg["OBS_NDAS_SFCandUPA_FN_TEMPLATE_PB2NC_OUTPUT"]

    # ---------------------------------------------------------------------
    # METplus tool name and derived filenames
    # ---------------------------------------------------------------------
    MetplusToolName = "Pb2NC"
    metplus_config_tmpl_fn = f"{MetplusToolName}_obs.conf"
    CDATE = cycle_date
    metplus_config_fn = f"{metplus_config_tmpl_fn}_NDAS_{CDATE}.conf"
    metplus_log_fn = f"metplus.log.{metplus_config_fn}_NDAS"

    # ---------------------------------------------------------------------
    # Output directories
    # ---------------------------------------------------------------------
    output_dir = Path(vxcfg["VX_OUTPUT_BASEDIR"], "metprd", MetplusToolName)
    staging_dir = Path(vxcfg["VX_OUTPUT_BASEDIR"], "stage", MetplusToolName)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------------
    # Resolve verification parameters via set_vx_params
    # ---------------------------------------------------------------------
    try:
        (
            grid_or_point,
            FIELDNAME_IN_OBS_INPUT,
            FIELDNAME_IN_FCST_INPUT,
            FIELDNAME_IN_MET_OUTPUT,
            FIELDNAME_IN_MET_FILEDIR_NAMES,
        ) = set_vx_params(obtype, field_group, accum_hh)
    except Exception as exc:
        lgr.error("Failed to get verification parameters: %s", exc)
        raise

    # ---------------------------------------------------------------------
    # Build the list of lead hours for which observation files exist
    # ---------------------------------------------------------------------
    vx_leadhr_list = set_leadhrs(
        date_init=f"{CDATE[:6]}00",  # YYMMDD00
        lhr_min=0,
        lhr_max=cfg["workflow"]["FCST_LEN_HRS"],
        lhr_intvl=vxcfg["VX_FCST_OUTPUT_INTVL_HRS"],
        base_dir=OBS_DIR,
        time_lag=0,
        fn_template=OBS_INPUT_FN_TEMPLATE,
        num_missing_files_max=vxcfg["NUM_MISSING_OBS_FILES_MAX"],
        skip_check_files=False,
        verbose=verbose,
    )

    if not vx_leadhr_list:
        raise RuntimeError("No lead hours found for observation files.")

    # ---------------------------------------------------------------------
    # Prepare METplus configuration variables
    # ---------------------------------------------------------------------
    vx_intvl = vxcfg["VX_FCST_OUTPUT_INTVL_HRS"]
    vx_hr_start = 0

    # Render METplus configuration file
    settings = {
        "metplus_tool_name": MetplusToolName.lower(),
        "MetplusToolName": MetplusToolName,
        "METPLUS_TOOL_NAME": MetplusToolName.upper(),
        "metplus_verbosity_level": vxcfg["METPLUS_VERBOSITY_LEVEL"],
        "cdate": CDATE,
        "vx_leadhr_list": ", ".join(map(str, vx_leadhr_list)),
        "metplus_config_fn": metplus_config_fn,
        "metplus_log_fn": metplus_log_fn,
        "obs_input_dir": OBS_DIR,
        "obs_input_fn_template": OBS_INPUT_FN_TEMPLATE,
        "output_dir": str(output_dir),
        "output_fn_template": OUTPUT_FN_TEMPLATE,
        "staging_dir": str(staging_dir),
        "vx_fcst_model_name": vxcfg.get("VX_FCST_MODEL_NAME", ""),
        "vx_intvl": vx_intvl,
        "vx_hr_start": vx_hr_start,
        "grid_or_point": grid_or_point,
        "fieldname_in_obs_input": FIELDNAME_IN_OBS_INPUT,
        "fieldname_in_fcst_input": FIELDNAME_IN_FCST_INPUT,
        "fieldname_in_met_output": FIELDNAME_IN_MET_OUTPUT,
        "fieldname_in_met_filedir_names": FIELDNAME_IN_MET_FILEDIR_NAMES,
        "obtype": obtype,
    }

    # Render the configuration file using the template
    conf_files = render_metplus_confs(
        cfg,
        settings,
        metplus_config_tmpl_fn,
        vx_leadhr_list,
        vxcfg["VX_TASKS"],
    )

    # Run METplus for each generated config file
    common_conf = Path(cfg["user"]["METPLUS_CONF"], "common.conf")
    for conf_file in conf_files:
        run_metplus(str(common_conf), conf_file)

    # ---------------------------------------------------------------------
    # Create completion flag file
    # ---------------------------------------------------------------------
    flag_dir = Path(cfg["workflow"]["WFLOW_FLAG_FILES_DIR"])
    flag_dir.mkdir(parents=True, exist_ok=True)
    flag_file = flag_dir / f"{obtype}_nc_obs_{CDATE[:6]}_ready.txt"
    flag_file.touch()

    lgr.info("Pb2NC completed successfully.")



def run_metplus(common_config: str, config_fn: str):
    """Invoke the METplus run script."""
    metplus_path = os.environ["METPLUS_ROOT"]
    subprocess.run(
        [
            f"{metplus_path}/ush/run_metplus.py",
            "-c",
            common_config,
            "-c",
            config_fn,
        ],
        check=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PB2NC NetCDF conversion for observation files"
    )
    parser.add_argument("--config", default="config.yaml", help="YAML experiment configuration file")
    parser.add_argument("--cycle_date", required=True, help="Eight‑digit cycle date (YYMMDDHH)")
    parser.add_argument("--obtype", required=True, help="Observation type (e.g., NDAS)")
    parser.add_argument("--field_group", required=True, help="Field group for the observation type")
    parser.add_argument("--accum_hh", required=True, type=int, help="Accumulation hour")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug output")
    args = parser.parse_args()

    main(
        args.config,
        args.cycle_date,
        args.obtype,
        args.field_group,
        args.accum_hh,
        args.verbose,
    )
