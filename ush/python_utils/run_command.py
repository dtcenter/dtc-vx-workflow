#!/usr/bin/env python3

import logging
import os
import subprocess


def run_command(cmd):
    """Runs system command in a subprocess

    Args:
        cmd (str): Command to execute
    Returns:
        Tuple of (exit code, std_out, std_err)
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        universal_newlines=True,
    )

    std_out, std_err = proc.communicate()

    # strip trailing newline character
    return (proc.returncode, std_out.rstrip("\n"), std_err.rstrip("\n"))


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

