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
    obs_dir = vxcfg[f"{obtype}_OBS_DIR"]
    obs_input_fn_template = vxcfg[f"OBS_{obtype}_FN_TEMPLATES"][1]
    if obtype == "NDAS":
        output_fn_template = vxcfg["OBS_NDAS_SFCandUPA_FN_TEMPLATE_PB2NC_OUTPUT"]
    else:
        raise ValueError(f"Invalid obtype for PB2NC: {obtype}")

    # ---------------------------------------------------------------------
    # METplus tool name and derived filenames
    # ---------------------------------------------------------------------
    MetplusToolName = "Pb2NC"
    metplus_config_tmpl_fn = f"{MetplusToolName}_obs.conf"
    metplus_config_fn = f"{metplus_config_tmpl_fn}_NDAS_{cycle_date}.conf"
    metplus_log_fn = f"metplus.log.{metplus_config_fn}_NDAS"

    # ---------------------------------------------------------------------
    # Output directories
    # ---------------------------------------------------------------------
    output_dir = Path(vxcfg["VX_OUTPUT_BASEDIR"], "metprd", MetplusToolName)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------------
    # Build the list of lead hours for which observation files exist
    # ---------------------------------------------------------------------
    vx_leadhr_list = set_leadhrs(
        date_init=cycle_date,
        lhr_min=0,
        lhr_max=cfg["workflow"]["FCST_LEN_HRS"],
        lhr_intvl=vxcfg["VX_FCST_OUTPUT_INTVL_HRS"],
        base_dir=obs_dir,
        time_lag=0,
        fn_template=obs_input_fn_template,
        num_missing_files_max=vxcfg["NUM_MISSING_OBS_FILES_MAX"],
        skip_check_files=False,
        verbose=verbose,
    )

    if not vx_leadhr_list:
        raise RuntimeError("No lead hours found for observation files.")

    # ---------------------------------------------------------------------
    # Prepare METplus configuration variables
    # ---------------------------------------------------------------------

    # Render METplus configuration file
    settings = {
        "METPLUS_TOOL_NAME": MetplusToolName.upper(),
        "metplus_verbosity_level": vxcfg["METPLUS_VERBOSITY_LEVEL"],
        "cdate": cycle_date,
        "vx_leadhr_list": ", ".join(map(str, vx_leadhr_list)),
        "metplus_config_fn": metplus_config_fn,
        "metplus_log_fn": metplus_log_fn,
        "obs_input_dir": obs_dir,
        "obs_input_fn_template": obs_input_fn_template,
        "output_dir": output_dir,
        "output_fn_template": output_fn_template,
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
    flag_file = flag_dir / f"{obtype}_nc_obs_{cycle_date[:6]}_ready.txt"
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
