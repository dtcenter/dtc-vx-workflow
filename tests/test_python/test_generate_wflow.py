""" Defines an integration test for generate_wflow script in the
ush directory """

import os
import sys
import tempfile
import unittest
from multiprocessing import Process
from pathlib import Path
from typing import Union

from uwtools.api.config import get_yaml_config

from python_utils import set_env_var
from python_utils.parse_test_list import ALL_TESTS
from python_utils.vx_mask_files import VX_MASK_FILE_EXTENSIONS

from generate_wflow import generate_wflow

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
USH_DIR = os.path.join(TEST_DIR, "..", "..", "ush")
WE2E_DIR = os.path.join(TEST_DIR, "..", "WE2E")
WFLOW_MASK_DIR = Path(TEST_DIR, "..", "..", "parm", "metplus", "vx_masks")
class Testing(unittest.TestCase):
    """ Class to run the tests. """
    def test_generate_wflow_community(self) -> None:

        """ Test that, for each workflow end-to-end test, the config file can successfully lead to
        the creation of an experiment directory. No jobs are submitted. """

        # ALL_TESTS is the list of WE2E test config files (paths relative to
        # WE2E_DIR) that run_we2e_tests.py can run.  Using it here ensures that
        # this test generates an experiment from each of those configs.
        for test in ALL_TESTS:
            self._run_generate_wflow_test_(os.path.join(WE2E_DIR, test))

    def setUp(self) -> None:
        set_env_var("DEBUG", False)
        set_env_var("VERBOSE", False)

    @staticmethod
    def _run_generate_wflow_test_(src_config_yaml_filename: Union[str, Path]) -> None:
        # run workflows in separate process to avoid conflict between community and nco settings.
        # src_config_yaml_filename is the absolute path to a single WE2E test
        # config file.
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
        # - platform.MET_INSTALL_DIR is set to a fake MET installation in a
        #   temporary directory, since setup.py looks for the file for each
        #   mask in verification.VX_MASKS, and MET may not be installed (e.g.
        #   in the GitHub CI).  Its share/met/poly directory contains an empty
        #   <name>.poly file for each mask in VX_MASKS that doesn't come with
        #   the workflow (i.e. isn't in parm/metplus/vx_masks), e.g. CONUS.
        #
        # update_from() adds these four settings to the test config's user and
        # platform sections (creating the sections if necessary), replacing any
        # values already set for them, and keeps the other keys in those
        # sections.  (Appending a second copy of a section instead would make
        # generation fail with a duplicate-key error.)
        #
        # The variable config set below contains only the settings in the WE2E
        # test's config file, not the full experiment configuration: the
        # defaults (from config_defaults.yaml) and the machine file are merged
        # in later, by generate_wflow (in load_config_for_setup() in setup.py).
        # config is a uwtools YAMLConfig object, which behaves like a dict.
        config = get_yaml_config(src_config_yaml_filename)
        with tempfile.TemporaryDirectory() as met_install_dir:
            met_poly_dir = Path(met_install_dir, "share", "met", "poly")
            met_poly_dir.mkdir(parents=True)
            # Get the list of masks in the test's config.  config.get() returns
            # None if there is no verification section, and also if the
            # section is empty ("verification:" with nothing under it).  If a
            # None is returned by config.get("verification"), the "or {}"
            # turns that None into an empty dict, so that .get("VX_MASKS", [])
            # still works (the .get() can't operate on a None).  If the test's
            # config doesn't set VX_MASKS, an empty list is returned instead of
            # a None (since the second argument to get() is []).  Thus, in this
            # case, vx_masks gets set to [], the same as the default in
            # config_defaults.yaml.
            vx_masks = (config.get("verification") or {}).get("VX_MASKS", [])
            for mask in vx_masks:
                # The paths that the mask's file would have if the mask came
                # with the workflow, one for each allowed extension (e.g.
                # .../vx_masks/AZCA.poly and .../vx_masks/AZCA.nc).  These are
                # only candidates; whether either file exists is checked next.
                wflow_mask_paths = [WFLOW_MASK_DIR / f"{mask}{ext}"
                                    for ext in VX_MASK_FILE_EXTENSIONS]
                mask_comes_with_wflow = any(path.is_file() for path in wflow_mask_paths)
                # If the mask doesn't come with the workflow, create an empty
                # file for it in the fake MET installation, so that setup.py
                # finds one.
                if not mask_comes_with_wflow:
                    (met_poly_dir / f"{mask}.poly").touch()
            config.update_from({
                "user": {"MACHINE": "LINUX", "ACCOUNT": "an_account"},
                "platform": {"MET_INSTALL_DIR": met_install_dir, "METPLUS_ROOT": "/dummy/path"},
            })
            # Write config, i.e. the test's settings plus the ones added above,
            # to ush/config.yaml (not in a temporary directory but under the
            # dtc-vx-workflow clone), replacing any file already there.  This
            # is the user config file that generate_wflow reads (run_workflow()
            # passes it USH_DIR and "config.yaml").  Each WE2E test overwrites
            # the previous test's file, and the last test's file is left behind
            # when this test finishes.  dump() needs a Path, not a str, so
            # USH_DIR is converted to a Path.
            config.dump(Path(USH_DIR) / "config.yaml")
            run_workflow(logfile)
