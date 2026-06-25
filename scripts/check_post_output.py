# pylint: disable=logging-fstring-interpolation
"""
Converted from scripts/check_post_output.sh, this script checks that the expected
post-processed forecast output files exist on disk, up to the allowed maximum
number of missing files.

The script is intended to be called from jobs/CHECK_POST_OUTPUT.sh.
"""

import argparse
import logging
import os

import uwtools.api.config as uwconfig

from python_utils import setup_logging
from set_leadhrs import set_leadhrs


def check_post_output(config_file: str, cdate: str, ensmem_index: int) -> None:
    """Check that post-processed forecast output files exist for a given cycle and member.

    Calls set_leadhrs() to verify that no more than NUM_MISSING_FCST_FILES_MAX files
    are absent from disk. Raises an exception if the missing-file threshold is exceeded.

    Parameters
    ----------
    config_file : str
        Path to the experiment configuration YAML.
    cdate : str
        Eight-digit cycle date in ``YYYYMMDDHH`` format.
    ensmem_index : int
        Ensemble member index (0 for deterministic runs, 1-based for ensemble members).
    """
    lgr = logging.getLogger(__name__)

    cfg = uwconfig.get_yaml_config(config=config_file)
    vxcfg = cfg["verification"]
    wfcfg = cfg["workflow"]
    enscfg = cfg["ensemble"]

    # Get time lag in seconds for this member; deterministic uses index 0
    i = max(ensmem_index - 1, 0)
    time_lag = int(enscfg["ENS_TIME_LAG_HRS"][i]) * 3600

    # Build forecast filename template, prepending subdir template if set
    subdir = vxcfg.get("FCST_SUBDIR_TEMPLATE", "")
    fn_template = os.path.join(subdir, vxcfg["FCST_FN_TEMPLATE"]) if subdir \
                  else vxcfg["FCST_FN_TEMPLATE"]

    lgr.info(
        f"Checking post-processed output files for cycle {cdate}, "
        f"member index {ensmem_index}"
    )
    lgr.debug(f"{fn_template=}")
    lgr.debug(f"{time_lag=}")

    set_leadhrs(
        date_init=cdate,
        lhr_min=0,
        lhr_max=wfcfg["FCST_LEN_HRS"],
        lhr_intvl=vxcfg["VX_FCST_OUTPUT_INTVL_HRS"],
        base_dir=vxcfg["VX_FCST_INPUT_BASEDIR"],
        time_lag=time_lag,
        fn_template=fn_template,
        num_missing_files_max=vxcfg["NUM_MISSING_FCST_FILES_MAX"],
    )

    lgr.info(f"Post-processed output file check completed successfully for cycle {cdate}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check that post-processed forecast output files exist on disk"
    )
    parser.add_argument(
        "--config", default="config.yaml", type=str,
        help="Path to the experiment configuration file in YAML format",
    )
    parser.add_argument(
        "--cycle_date", required=True, type=str,
        help="Eight-digit cycle date (YYYYMMDDHH)",
    )
    parser.add_argument(
        "--ensmem_index", required=True, type=int,
        help="Ensemble member index (0 for deterministic, 1-based for ensemble members)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose debug output",
    )
    args = parser.parse_args()

    setup_logging(debug=args.verbose)

    check_post_output(args.config, args.cycle_date, args.ensmem_index)
