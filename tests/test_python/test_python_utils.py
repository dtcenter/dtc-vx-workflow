"""
Unit tests for python utilities.

To run them, issue the following command from the top-level directory:
    python3 -m unittest -b tests/test_python/test_python_utils.py

All conda packages needed to run the workflow must be loaded for unit tests to pass

"""

#pylint: disable=invalid-name

import glob
import os
import shutil
import tempfile
import unittest

import python_utils as util


class Testing(unittest.TestCase):
    """ Define the tests"""

    def test_pattern_finding(self):
        """ Test that find_pattern_in_file can work with a string or a
        file path"""

        # Test given a file path
        pattern = "^[ ]*<scheme>(lsm_ruc)</scheme>[ ]*$"
        test_file = os.path.join(
           self.ushdir,
           "test_data",
           "suite_FV3_GSD_SAR.xml",
           )
        match = util.find_pattern_in_file(pattern, test_file)
        self.assertEqual(("lsm_ruc",), match)

        # Test given a string
        with open(test_file, encoding='utf-8') as file_:
            content = file_.read()

        util.find_pattern_in_str(pattern, content)
        self.assertEqual(("lsm_ruc",), match)

    def test_check_for_preexist_dir_file(self):
        """ Test that when an existing directory should be renamed, it
        still exists and that a new directory is made"""

        with tempfile.TemporaryDirectory(
            dir=os.path.abspath("."),
            prefix="preexist_space",
            ) as tmp_dir:

            # Given a preexisting directory, move it and test that they both
            # exist.
            existing_dir = os.path.join(tmp_dir, "dir")
            os.makedirs(existing_dir)
            util.check_for_preexist_dir_file(existing_dir, "rename")
            dirs = glob.glob(f"{existing_dir}_*")
            self.assertEqual(len(dirs), 1)

    def test_check_var_valid_value(self):
        """ Test that a string is available in a given list. """
        self.assertTrue(util.check_var_valid_value("rice", ["egg", "spam", "rice"]))

    def test_filesys_cmds(self):
        """ Test the functions that perform filesystem commands"""

        with tempfile.TemporaryDirectory(
            dir=os.path.abspath("."),
            prefix="filesys_space",
            ) as tmp_dir:

            testable_path = os.path.join(
                tmp_dir,
                "dir",
                )

            # Make sure a desired path is created
            os.makedirs(testable_path)
            self.assertTrue(os.path.exists(testable_path))

            # Make sure a file is copied
            shutil.copy(f"{self.ushdir}/python_utils/misc.py", f"{testable_path}/miscs.py")
            self.assertTrue(os.path.exists(f"{testable_path}/miscs.py"))

    def test_run_command(self):
        """ Test the return of the run_command task is as expected."""
        self.assertEqual(util.run_command("echo hello"), (0, "hello", ""))

    def test_create_symlink_to_file(self):
        """ Test that a simlink is created as expected."""

        target = f"{self.test_dir}/test_python_utils.py"
        with tempfile.TemporaryDirectory(
            dir=os.path.abspath("."),
            prefix="simlink_space",
            ) as tmp_dir:

            symlink = os.path.join(
                tmp_dir,
                "test_python_utils.py"
                )
            util.create_symlink_to_file(target, symlink)

    def test_print_input_args(self):
        """ Test that print_input_args can count the args. """
        valid_args = {"arg1": 1, "arg2": 2, "arg3": 3, "arg4": 4}
        self.assertEqual(util.print_input_args(valid_args), 4)

    def test_config_parser(self):
        """ Test loading different config files """
        cfg = {"HRS": ["1", "2"]}
        shell_str = util.cfg_to_shell_str(cfg)
        self.assertIn('HRS=( "1" "2" )\n', shell_str)
        # ini file
        file_path = os.path.join(
            self.ushdir,
            "python_utils",
            "test_data",
            "Externals.cfg",
            )
        cfg = util.load_ini_config(file_path)
        self.assertIn(
            "regional_workflow", util.get_ini_value(cfg, "regional_workflow", "repo_url")
        )

    def setUp(self):
        """setUp is where we do preparation for running the unittests.
        If you need to download files for running test cases, prepare common stuff
        for all test cases etc, this is the best place to do it"""

        util.set_env_var("DEBUG", "FALSE")
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.ushdir = os.path.join(self.test_dir, "..", "..", "ush")

if __name__ == "__main__":
    unittest.main()
