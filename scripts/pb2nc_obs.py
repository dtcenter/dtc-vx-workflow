# pylint: disable=logging-fstring-interpolation
"""
Converted from scripts/pb2nc_obs.sh, this script calls the METplus "PB2NC" tool to convert
PrepBUFR observation files to NetCDF.

The script is intended to be called from jobs/PB2NC_OBS.sh
"""

import argparse
import os
import logging
import subprocess
from datetime import datetime
from pathlib import Path

import uwtools.api.config as uwconfig

# Import utilities and helpers
from eval_metplus_timestr_tmpl import eval_metplus_dt_tmpl
from python_utils import setup_logging, render_metplus_confs


def pb2nc(config_file: str, cycle_date: str, obtype: str, verbose: bool = False):
    # pylint: disable=too-many-locals
    """Main routine for PB2NC observation conversion.

    Parameters
    ----------
    config_file : str
        Path to the experiment configuration YAML.
    cycle_date : str
        Eight‑digit cycle date in ``YYMMDDHH`` format.
    obtype : str
        Observation type (e.g. ``NDAS``).
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
    metplus_tool_camel_case = "Pb2nc"
    metplus_config_tmpl_fn = f"{metplus_tool_camel_case}_obs.conf"
    metplus_config_fn = f"{metplus_config_tmpl_fn}_NDAS_{cycle_date}.conf"
    metplus_log_fn = f"metplus.log.{metplus_config_fn}_NDAS"

    # ---------------------------------------------------------------------
    # Output directories
    # ---------------------------------------------------------------------
    output_dir = Path(vxcfg["VX_OUTPUT_BASEDIR"], "metprd", f"{metplus_tool_camel_case}_obs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------------
    # Build the list of lead hours for which observation files exist
    # ---------------------------------------------------------------------

    vx_leadhr_list=[]
    cycle_dt=datetime.strptime(cycle_date, '%Y%m%d%H')
    for time in vxcfg[f"OBS_RETRIEVE_TIMES_{obtype}_{cycle_date[0:8]}"]:
        validdt=datetime.strptime(time, '%Y%m%d%H')

        lead = validdt - cycle_dt
        leadhr=int(lead.total_seconds()/3600)
        file = eval_metplus_dt_tmpl(f"{obs_dir}/{obs_input_fn_template}", cycle_dt,validdt)
        if os.path.exists(file):
            vx_leadhr_list.append(leadhr)

    if not vx_leadhr_list:
        raise RuntimeError("No lead hours found for observation files.")

    # ---------------------------------------------------------------------
    # Prepare METplus configuration variables
    # ---------------------------------------------------------------------

    # Render METplus configuration file
    settings = {
        "METPLUS_TOOL_NAME": metplus_tool_camel_case.upper(),
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
    flag_file = flag_dir / f"{obtype}_nc_obs_{cycle_date}_ready.txt"
    flag_file.touch()

    lgr.info(f"{metplus_tool_camel_case} completed successfully.")



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
    parser.add_argument("--config", default="config.yaml", help="YAML experiment config file")
    parser.add_argument("--cycle_date", required=True, help="Eight‑digit cycle date (YYMMDDHH)")
    parser.add_argument("--obtype", required=True, help="Observation type (e.g., NDAS)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug output")
    args = parser.parse_args()

    pb2nc(
        args.config,
        args.cycle_date,
        args.obtype,
        args.verbose,
    )
