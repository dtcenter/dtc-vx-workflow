#!/usr/bin/env python3
import argparse
import ast

from string import Template
from pathlib import Path
from pprint import pprint

import uwtools.api.config as uwconfig
from set_leadhrs import set_leadhrs

def check_post_output(config, ensmem_index, cycle_date):
    """
    Checks for the existence of forecast files corresponding to a list of lead
    hours derived from the some of the experiment settings (the forecast length
    and output interval).  If too many files are missing, it fails with an
    exception.

    Args:
        config        (str): Full path to experiment configuration file.
        ensmem_index  (int): The index of the ensemble forecast member
                             (0 for a deterministic forecast).
        cycle_date    (str): Date string for initial time in YYYYMMDD[mmss]
                             format, where minutes and seconds are optional.

    Returns:
        None
    """

    cfg = uwconfig.get_yaml_config(config=config)
    vxcfg = cfg["verification"]

    lhr_min = 0
    lhr_max = cfg["workflow"]["FCST_LEN_HRS"]
    lhr_intvl = vxcfg["VX_FCST_OUTPUT_INTVL_HRS"]
    fcst_input_base_dir = vxcfg["VX_FCST_INPUT_BASEDIR"]
    num_missing_files_max = vxcfg["NUM_MISSING_FCST_FILES_MAX"]
    fcst_subdir_template = vxcfg["FCST_SUBDIR_TEMPLATE"]
    fcst_fn_template = vxcfg["FCST_FN_TEMPLATE"]

    # Time lag (in seconds) for this ensemble member; 0 for deterministic runs.
    time_lag = 0
    if cfg["ensemble"]["DO_ENSEMBLE"]:
        time_lag_hrs = ast.literal_eval(cfg["ensemble"]["ENS_TIME_LAG_HRS"])[ensmem_index-1]
        time_lag = time_lag_hrs*3600

    # zfill(n) pads the string on the left with zeros to width n.
    subvars = {
        "ensmem_name": f"mem{str(ensmem_index).zfill(vxcfg['VX_NDIGITS_ENSMEM_NAMES'])}",
        "time_lag": time_lag,
    }
    #
    # Substitute for bash-style variables (which are really just placeholders
    # now) in FCST_SUBDIR_TEMPLATE and FCST_FN_TEMPLATE with the values for
    # those placeholders specified in subvars.  Then combine this to obtain
    # a path (usually relative) to the forecast data files.  Note that this
    # path will in general still contain MET-style placeholders (but not bash-
    # style or jinja2-style placeholders).
    #
    # Template(some_template).substitute(values_dict) replaces each placeholder
    # of the form $... or ${...} (i.e. bash-style variables) in some_template
    # with the value of the key in values_dict that has the same name as the
    # placeholder (without the $ and/or {}).
    #
    fn_template = str(Path(Template(fcst_subdir_template).substitute(subvars),
                           Template(fcst_fn_template).substitute(subvars)))

    # Require verbose output in order to get messages in the log file specifying
    # which files were/weren't found.
    set_leadhrs(cycle_date, lhr_min, lhr_max, lhr_intvl,
                fcst_input_base_dir, time_lag, fn_template,
                num_missing_files_max, verbose=True)

    return


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="""
            Check for the existence of forecast files; fail if too many are missing.
        """,
    )
    parser.add_argument("-c", "--config", required=True,
                        help="Full path to experiment configuration file")
    parser.add_argument("-ei", "--ensmem_index", type=int, required=True,
                        help='The index for this ensemble member (0 for deterministic)')
    parser.add_argument("-d", "--cycle_date", type=str, required=True,
                        help="Initial date in YYYYMMDDHH[mmss] format")

    args = parser.parse_args()

    check_post_output(**vars(args))

