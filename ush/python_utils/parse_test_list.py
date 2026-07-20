#!/usr/bin/env python3

"""
This file provides utilities for gathering end-to-end test names
Supported formats include:

    a) A test name or list of test names.
    b) A subdirectory name under test_configs/
    c) The name of a file (full or relative path) containing a list of test names.
    d) "all" to run all tests
"""

import os
import logging
import glob
from textwrap import dedent
from pathlib import Path

TESTS_WE2E_DIR = Path(__file__).absolute().parents[2] / "tests" / "WE2E"

CONFIG_YAML_GLOB = "test_configs/**/config*.yaml"

ALL_TESTS = glob.glob(CONFIG_YAML_GLOB, recursive=True, root_dir=TESTS_WE2E_DIR)
TEST_DIRS = next(os.walk(os.path.join(TESTS_WE2E_DIR, "test_configs")))[1]

TEST_FILE_PREFIX = "config."
TEST_FILE_SUFFIX = ".yaml"

def get_pretty_list(test_list):
    return "\n".join(str(x) for x in test_list)

def get_tests_to_run(args_tests, names_only=False):
    tests_to_check = _get_tests_to_check(args_tests)
    tests_to_run = _check_tests(tests_to_check)
    if names_only:
        return _get_test_names(tests_to_run)
    return tests_to_run

def _get_tests_to_check(args_tests):
    # If args.tests is a list of length more than one, we assume it is a list of test names
    if len(args_tests) > 1:
        logging.debug(f"User specified a list of tests:\n{args_tests}")
        return args_tests

    # First see if args.tests is a valid test name
    user_spec_tests = args_tests
    logging.debug(f"Checking if {user_spec_tests} is a valid test name")
    match = _check_test(user_spec_tests[0])
    if match:
        return user_spec_tests

    # If not a valid test name, check if it is a test suite
    logging.debug(f"Checking if {user_spec_tests} is a valid test suite")
    if user_spec_tests[0] == "all":
        tests_to_check = _get_test_names(ALL_TESTS)
        logging.debug(f"Will check all tests:\n{tests_to_check}")
        return tests_to_check

    if user_spec_tests[0] in TEST_DIRS:
        # If a subdirectory under test_configs/ is specified, run all
        # tests in that directory
        logging.debug(
            f"{user_spec_tests[0]} is one of the testing directories:\n{TEST_DIRS}"
        )
        logging.debug(
            f"Will run all tests in test_configs/{user_spec_tests[0]}"
        )
        tests_in_dir = glob.glob(
            f"test_configs/{user_spec_tests[0]}/config*.yaml", recursive=True,
            root_dir=TESTS_WE2E_DIR
        )
        return _get_test_names(tests_in_dir)

    # If we have gotten this far then the only option left for user_spec_tests is a
    # file containing test names
    logging.debug(
        f"Checking if {user_spec_tests} is a file containing test names"
    )
    if not Path(user_spec_tests[0]).is_file():
        raise FileNotFoundError(
            dedent(
                f"""
        The specified 'tests' argument '{user_spec_tests}'
        does not appear to be a valid test name, a valid test suite, a subdirectory
        under test_configs/, or a file containing valid test names.

        Check your inputs and try again.
        """
            )
        )

    # read file to get list of files to check
    with open(user_spec_tests[0], encoding="utf-8") as f:
        tests_to_check = [x.rstrip() for x in f]
    return tests_to_check

def _get_test_names(test_list) -> list[str]:
    test_names = []
    for f in test_list:
        filename = Path(f).name
        # We just want the test name in this list, so cut out the
        # "config." prefix and ".yaml" extension
        if len(filename) > 12 and filename.startswith(TEST_FILE_PREFIX) and filename.endswith(TEST_FILE_SUFFIX):
            test_names.append(filename[7:-5])
        else:
            logging.debug(f"Skipping non-test file {filename}")

    return test_names

def _check_tests(tests: list) -> list:
    """
    Checks that all tests in a provided list of tests are valid

    Args:
        tests (list): List of potentially valid test names

    Returns:
        tests_to_run: List of configuration files corresponding to test names
    """
    logging.info("Checking that all tests are valid")

    # Check that there are no duplicate test filenames
    _check_for_duplicate_tests()

    tests_to_run = []
    for test in tests:
        # Skip blank/empty testnames; this avoids failure if newlines or spaces are included
        if not test or test.isspace():
            continue
        # Skip if string has an octothorpe
        if "#" in test:
            logging.debug(
                f"Assuming line is a comment due to presence of '#' character:\n{test}"
            )
            continue
        match = _check_test(test)
        if not match:
            raise FileNotFoundError(f"Could not find test {test}")
        tests_to_run.append(match)
    # Because some test files are symlinked to other tests, check that we don't
    # include the same test twice
    for testfile in tests_to_run.copy():
        testfile = Path(testfile)
        if testfile.is_symlink() and testfile.resolve() in tests_to_run:
            logging.warning(
                dedent(
                    f"""WARNING: test file {testfile} is a symbolic link to a
                            test file ({testfile.resolve()}) that is also included in
                            the test list. Only the latter test will be run."""
                )
            )
            tests_to_run.remove(str(testfile))
    if len(tests_to_run) != len(set(tests_to_run)):
        logging.warning(
            "\nWARNING: Duplicate test names were found in list. "
            "Removing duplicates and continuing.\n"
        )
        tests_to_run = list(set(tests_to_run))
    return tests_to_run

def _check_for_duplicate_tests():
    testfilenames = []
    for testfile in ALL_TESTS:
        testfile = Path(testfile)
        if testfile.name in testfilenames:
            duplicates = glob.glob(f"test_configs/**/{testfile.name}", recursive=True, root_dir=TESTS_WE2E_DIR)
            raise ValueError(
                dedent(
                    f"""
                            Found duplicate test file names:
                            {duplicates}
                            Ensure that each test file name under the test_configs/ directory
                            is unique.
                            """
                )
            )
        testfilenames.append(testfile.name)

def _check_test(test: str):
    """
    Checks that a string corresponds to a valid test name

    Args:
        test (str): Potential test name

    Returns:
        config: Name of the test configuration file (empty string if no test file is found)
    """
    # potential test file for input test name
    test_config = f"{TEST_FILE_PREFIX}{test.strip()}{TEST_FILE_SUFFIX}"
    config = ""
    for testfile in ALL_TESTS:
        if test_config in testfile:
            logging.debug(f"found test {test}, testfile {testfile}")
            config = TESTS_WE2E_DIR / Path(testfile)
    return config
