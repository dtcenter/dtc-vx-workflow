""" Defines an integration test for generate_wflow script in the
ush directory """

import glob
import os
import shutil
import sys
import unittest
from multiprocessing import Process
from pathlib import Path
from typing import Union

from python_utils import (
    run_command,
    set_env_var,
    get_env_var,
)

from generate_wflow import generate_wflow

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
USH_DIR = os.path.join(TEST_DIR, "..", "..", "ush")
WE2E_DIR = os.path.join(TEST_DIR, "..", "WE2E")
class Testing(unittest.TestCase):
    """ Class to run the tests. """
    def test_generate_wflow_community(self) -> None:

        """ Test that, for each workflow end-to-end test, the config file can successfully lead to
        the creation of an experiment directory. No jobs are submitted. """

        for test in glob.glob(os.path.join(WE2E_DIR,"test_configs/*/config*yaml")):
            self._run_generate_wflow_test_(test)

    def setUp(self) -> None:
        set_env_var("DEBUG", False)
        set_env_var("VERBOSE", False)

    @staticmethod
    def _run_generate_wflow_test_(src_config_yaml_filename: Union[str, Path]) -> None:
        # run workflows in separate process to avoid conflict between community and nco settings
        def run_workflow(logfile):
            p = Process(target=generate_wflow, args=(USH_DIR, "config.yaml", logfile))
            p.start()
            p.join()
            exit_code = p.exitcode
            if exit_code != 0:
                with open(logfile, 'r', encoding='utf-8') as fin:
                    print(fin.read())
                sys.exit(exit_code)

        logfile = "log.generate_wflow"
        sed = get_env_var("SED")
        shutil.copy(src_config_yaml_filename, f"{USH_DIR}/config.yaml")
        # Append mandatory variables to end of config file
        addtext = "\nuser:\n  MACHINE: LINUX\n  ACCOUNT: an_account"
        addtext += "\nplatform:\n  MET_INSTALL_DIR: /dummy/path\n  METPLUS_ROOT: /dummy/path"
        with open(f"{USH_DIR}/config.yaml", "a", encoding="utf-8") as f:
            f.write(addtext)

        # If running CI, point config.yaml to correct location for fix files
        if fix_files := get_env_var("CI_FIX_FILES"):
            run_command(
                f"""{sed} -i 's/MACHINE: HERA/MACHINE: LINUX/g' {USH_DIR}/config.yaml"""
            )
            machine_file = f"{USH_DIR}/machine/linux.yaml"
            sed_command = f"{sed} -i 's|/home/username/DATA/UFS|{fix_files}|g' " \
                          f"{machine_file}"
            run_command(sed_command)
        run_workflow(logfile)
