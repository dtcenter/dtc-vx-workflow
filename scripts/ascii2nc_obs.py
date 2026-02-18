#!/usr/bin/env python3
"""
Converted from scripts/ascii2nc_obs.sh
"""
# pylint: disable=logging-fstring-interpolation

import argparse
import os
import logging
import subprocess
from datetime import datetime
from pathlib import Path

import uwtools.api.config as uwconfig

from eval_metplus_timestr_tmpl import eval_metplus_dt_tmpl
from python_utils import setup_logging, render_metplus_confs

# ------------------------------------------------------------------
# Core functions ----------------------------------------------------
# ------------------------------------------------------------------


def main(config_file, cdate, obtype):
    # pylint: disable=too-many-locals
    """Call METplus ASCII2NC tool to convert ASCII observation files to NetCDF.

    Parameters
    ----------
    config_file : str
        Path to the YAML experiment configuration file.
    cdate : str
        Cycle date in ``YYYYMMDDHH`` format that identifies the forecast
        window to process.
    obtype : str
        Observation type, e.g. ``"AERONET"`` or ``"AIRNOW"``.

    Notes
    -----
    The function reads the supplied configuration, determines the
    appropriate input/output directories and file templates for the
    requested observation type, identifies the lead‑hour files that
    exist, renders a METplus configuration from a Jinja template,
    invokes the METplus driver, and finally creates a flag file that
    downstream tasks use to detect completion.

    Returns
    -------
    None

    """
    metplus_tool_camel_case = "Ascii2nc"
    lgr = logging.getLogger(__name__)
    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    vxcfg = cfg["verification"]

    output_dir = Path(vxcfg["VX_OUTPUT_BASEDIR"], "metprd", "Ascii2nc_obs")
    # Make sure the MET/METplus output directory(ies) exists.
    os.makedirs(output_dir, exist_ok=True)

    if obtype == "AERONET":
        obs_in_dir = vxcfg["AERONET_OBS_DIR"]
        obs_in_fn_tmpl = vxcfg["OBS_AERONET_FN_TEMPLATES"][1]
        output_fn_template = f'{vxcfg["OBS_AERONET_FN_TEMPLATE_ASCII2NC_OUTPUT"]}'
        input_format = "aeronetv3"
    elif obtype == "AIRNOW":
        obs_in_dir = vxcfg["AIRNOW_OBS_DIR"]
        obs_in_fn_tmpl = vxcfg["OBS_AIRNOW_FN_TEMPLATES"][1]
        output_fn_template = f'{vxcfg["OBS_AIRNOW_FN_TEMPLATE_ASCII2NC_OUTPUT"]}'
        input_format = vxcfg["AIRNOW_INPUT_FORMAT"]
    else:
        raise ValueError(f"Invalid OBTYPE for {metplus_tool_camel_case.upper()}: {obtype}")

    vx_leadhr_list = []
    cycle_dt = datetime.strptime(cdate, '%Y%m%d%H')
    for time in vxcfg[f"OBS_RETRIEVE_TIMES_{obtype}_{cdate[0:8]}"]:
        validdt = datetime.strptime(time, '%Y%m%d%H')

        lead = validdt - cycle_dt
        leadhr = int(lead.total_seconds()/3600)
        file = eval_metplus_dt_tmpl(cycle_dt, validdt, 0, f"{obs_in_dir}/{obs_in_fn_tmpl}", True)
        if os.path.exists(file):
            vx_leadhr_list.append(leadhr)

    if not vx_leadhr_list:
        raise RuntimeError("No lead hours found for observation files.")

    # Set the names of the template METplus configuration file, the resulting rendered conf file,
    # and the METplus log file
    metplus_config_tmpl_fn = "Ascii2nc_obs.conf"
    metplus_config_fn = f"{metplus_tool_camel_case}_{obtype}.conf.0"
    metplus_log_fn = f"metplus.log.{metplus_config_fn[:-7]}_{cdate}.0"

    # Define variables that appear in the jinja template, add to existing settings dict.
    settings = {
        'metplus_verbosity_level': vxcfg['METPLUS_VERBOSITY_LEVEL'],
        'METPLUS_TOOL_NAME': metplus_tool_camel_case.upper(),
        # Date and forecast hour information.
        'cdate': cdate,
        'vx_leadhr_list': ', '.join(map(str, vx_leadhr_list)),
        # Input and output directory/file information.
        'metplus_config_fn': metplus_config_fn,
        'metplus_log_fn': metplus_log_fn,
        'obs_input_dir': obs_in_dir,
        'obs_input_fn_template': obs_in_fn_tmpl,
        'output_dir': output_dir,
        'output_fn_template': output_fn_template,
        # Field information.
        'obtype': obtype,
        'input_format': input_format,
    }

    conf_file = render_metplus_confs(cfg, settings, metplus_config_tmpl_fn, vx_leadhr_list, 1)
    lgr.debug(f"{conf_file=}")

    lgr.info(f"Running {metplus_tool_camel_case.upper()} with METplus")
    run_metplus(os.path.join(cfg['user']['METPLUS_CONF'], "common.conf"), conf_file[0])

    lgr.info(f"Making completion flag file for {obtype}, cycle {cdate}")
    create_flag_file(cfg, obtype, cdate)
    lgr.info(f"{metplus_tool_camel_case} completed successfully.")


def run_metplus(common_config, config_fn):
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
    """Creates the flag file notifying downstream tasks that files are ready"""
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

    main(pargs.config, pargs.cycle_date, pargs.obtype)
