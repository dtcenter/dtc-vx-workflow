""" Defines an integration test for generate_wflow script in the
ush directory """

import glob
import os
import sys
import unittest
from multiprocessing import Process
from pathlib import Path
from typing import Union

from uwtools.api.config import get_yaml_config

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
        # Add dummy values of the settings that generation requires but that
        # the WE2E test configs don't specify.  (In real WE2E runs,
        # run_we2e_tests.py adds MACHINE and ACCOUNT, and the machine file
        # provides the MET and METplus paths.)
        #
        # - In setup.py, user.MACHINE is read from the user config alone (to
        #   find the machine file ush/machine/<machine>.yaml), so its default
        #   in config_defaults.yaml is never used.  Here, this parameter is set
        #   to "LINUX" so that the unit test can run on any computer.
        #
        # - user.ACCOUNT, platform.MET_INSTALL_DIR, and platform.METPLUS_ROOT
        #   must not be empty, but config_defaults.yaml sets them to empty
        #   strings, and linux.yaml doesn't set them.  They are set here rather
        #   than in linux.yaml so that real users on Linux who forget to set
        #   the MET and METplus paths still get an error at generation.
        #
        # update_from() adds these four settings to the test config's user and
        # platform sections (creating the sections if necessary), replacing any
        # values already set for them, and keeps the other keys in those
        # sections.  (Appending a second copy of a section instead would create
        # a duplicate key, and the test config's own settings in that section
        # would be lost.)
        config = get_yaml_config(src_config_yaml_filename)
        config.update_from({
            "user": {"MACHINE": "LINUX", "ACCOUNT": "an_account"},
            "platform": {"MET_INSTALL_DIR": "/dummy/path", "METPLUS_ROOT": "/dummy/path"},
        })
        config.dump(Path(USH_DIR) / "config.yaml")

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
