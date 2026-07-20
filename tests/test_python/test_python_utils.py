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
from pathlib import Path
import tempfile
import unittest

import python_utils as util


class Testing(unittest.TestCase):
    """ Define the tests"""

    def test_case_handlers(self):
        """ Test that the case handling string manipulators work as
        expected. """
        self.assertEqual(util.uppercase("upper"), "UPPER")
        self.assertEqual(util.lowercase("LOWER"), "lower")

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

    def test_parse_test_list_get_tests_to_run(self):
        """ Test parsing of different --tests arguments formats """
        # get all existing tests from tests/WE2E/test_configs directory
        test_configs_dir = Path(self.ushdir).parent / "tests" / "WE2E" / "test_configs"
        test_categories = [f.name for f in os.scandir(test_configs_dir) if f.is_dir()]
        we2e_tests = {}
        for test_category in test_categories:
            tests = [f.name[7:-5] for f in os.scandir(os.path.join(test_configs_dir, test_category))
                     if f.is_file()]
            we2e_tests[test_category] = tests

        total_test_num = sum(len(tests) for tests in we2e_tests.values())
        all_tests = [item for tests in we2e_tests.values() for item in tests]

        # sub tests to run to test different values for --tests argument and their expected results
        # each test contains:
        # * name of the test to identify it if it fails
        # * list of arguments to pass to the --tests argument
        # * expected number of tests that were found
        # * exception that is expected to be raised (set to None if no exception is expected)
        # Note: number of expected tests for tests that raise exceptions are set to the expected
        #  number of valid tests found if logic is revised to ignore/warn instead of error when a
        #  bad value is provided, enhanced to support multiple test categories or categories in
        #  file list files, etc. These tests are noted with "(not supported)" in the name.

        test_cases = [
            (
                "all",
               ["all"],
               total_test_num, None
            ),
            (
                "single test",
                 ["MET_verification_winter_wx"],
                 1, None
            ),
            (
                "single test invalid",
                 ["pizza"],
                 0, FileNotFoundError
            ),
            (
                "single test file name (not supported)",
                 ["config.MET_verification_winter_wx.yaml"],
                 1, FileNotFoundError
            ),
            (
                "multiple tests",
                 ["MET_verification_winter_wx", "vx-det_multicyc_fcst-overlap_ncep-hrrr"],
                 2, None
            ),
            (
                "all tests listed out",
                 all_tests,
                 total_test_num, None
            ),
            (
                "multiple tests one invalid",
                 ["MET_verification_winter_wx", "pudding"],
                 1, FileNotFoundError
            ),
            (
                "subdirectory invalid",
                 ["olives"],
                 0, FileNotFoundError
            ),
            (
                "2 subdirectories (not supported)",
                 ["deterministic", "ensemble"],
                 len(we2e_tests["deterministic"] + we2e_tests["ensemble"]), FileNotFoundError
            ),
        ]

        # add test cases for each subdirectory
        # list of test names and temporary file containing list of test names
        for test_cat, tests in we2e_tests.items():
            test_cases.append((
                f"{test_cat} subdir",
                [test_cat],
                len(tests), None
            ))
            test_cases.append((
                f"file path - {test_cat} subdir",
                [self.create_tmp_test_file(tests)],
                len(tests), None
            ))

        # name of file path using temporary files
        test_cases.append((
            "file path - all tests",
            [self.create_tmp_test_file(all_tests)],
            total_test_num, None
        ))

        # file path that contains an invalid test name
        test_cases.append((
            "file path - invalid test name",
            [self.create_tmp_test_file(["MET_verification_winter_wx", "pizza"])],
            1, FileNotFoundError
        ))

        # file path that contains a test category (not supported)
        test_cases.append((
            "file path - category (not supported)",
            [self.create_tmp_test_file(["deterministic"])],
            len(we2e_tests["deterministic"]), FileNotFoundError
        ))

        # test both options for names_only argument to get_tests_to_run function
        for names_only in (True, False):
            for name, inputs, expected, exception in test_cases:
                with self.subTest(msg=name, inputs=inputs, expected=expected):
                    if exception:
                        with self.assertRaises(exception):
                            util.get_tests_to_run(inputs, names_only=names_only)
                    else:
                        actual_results = util.get_tests_to_run(inputs, names_only=names_only)
                        self.assertEqual(len(actual_results), expected)
                        if not names_only:
                            for result in actual_results:
                                self.assertIn(str(test_configs_dir), str(result))

    def create_tmp_test_file(self, contents: list) -> str:
        """Helper to create a temporary file and automatically schedule its deletion."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write("\n".join(contents))
            file_path = tmp.name

        self.addCleanup(os.remove, file_path)
        return file_path

    def setUp(self):
        """setUp is where we do preparation for running the unittests.
        If you need to download files for running test cases, prepare common stuff
        for all test cases etc, this is the best place to do it"""

        util.set_env_var("DEBUG", "FALSE")
        self.test_dir = Path(__file__).resolve().parent
        self.ushdir = self.test_dir.parents[1] / "ush"

if __name__ == "__main__":
    unittest.main()
