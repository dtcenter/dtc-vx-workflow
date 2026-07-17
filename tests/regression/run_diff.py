#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path
import io
from contextlib import redirect_stdout
from dataclasses import dataclass
import logging
from datetime import datetime

from regression_common import DEFAULT_REGRESSION_DIR, NOT_RUN

# get function from WE2E script to get tests to run

USH_DIR = Path(__file__).absolute().parents[2] / "ush"
sys.path.insert(0, str(USH_DIR))

from python_utils.parse_test_list import get_tests_to_run, get_pretty_list

# class to store test results - status and any details regarding differences
@dataclass
class TestResults:
    status: str = NOT_RUN
    details: str = "No details to report"

# keywords to search in file paths to skip diff if found
SKIP_KEYWORDS = [
    "vx_wflow.xml",
    "var_defns.yaml",
    "vx_wflow_lock.db",
    "rocoto_defns.yaml",
    "vx_wflow.db",
    "config.yaml",
    "launch_vx_wflow.sh",
    "log.generate_wflow",
    ".conf",
    "/log/",
    "/stage/",
]

def main():
    args = read_args()

    # set up logging
    log_file = setup_logging(args)

    if not Path(args.metplus).exists():
        print(f"ERROR: METplus directory does not exist: {args.metplus}")
        sys.exit(1)

    sys.path.insert(0, str(args.metplus))
    from metplus.util import diff_util
    diff_util.SKIP_KEYWORDS = SKIP_KEYWORDS

    tests_to_diff = get_tests_to_run(args.tests, names_only=True)

    msg = (
        "Running diff tests"
        f"\nBASELINE: {Path(args.baseline_dir).resolve()}"
        f"\nNEW     : {Path(args.test_dir).resolve()}"
        f"\n\nTests to Diff:\n{get_pretty_list(tests_to_diff)}"
        f"\n\nUsing SKIP_KEYWORDS:\n{get_pretty_list(SKIP_KEYWORDS)}\n"
    )
    logging.info(msg)
    if not args.log_to_terminal:
        print(msg)

    test_results = init_test_results(tests_to_diff, args)

    for test_name, test_result in test_results.items():
        if test_result.status != NOT_RUN:
            continue

        print(f"Diffing {test_name}...")
        baseline_test = Path(args.baseline_dir) / test_name
        new_test = Path(args.test_dir) / test_name

        # create text stream to capture diff output for each test
        text_stream = io.StringIO()
        with redirect_stdout(text_stream):
            diff_files = diff_util.compare_dir(str(baseline_test), str(new_test), debug=args.debug)

        # save detailed report of diff test
        test_result.details = text_stream.getvalue().strip()

        if not diff_files:
            test_result.status = 'SUCCEEDED'
            continue

        test_result.status = 'FAILED (diffs found)'

    longest_test_len = len(max(test_results, key=len))

    logging.info("SUMMARY:")
    for test_name, test_result in test_results.items():
        logging.info(f"{test_name.ljust(longest_test_len+1)}:  {test_result.status}")

    logging.info("\nDETAILS:")
    for test_name, test_result in test_results.items():
        logging.info(f"{'-' * 80}\n{test_name}: {test_result.status}\n{'-' * 80}")
        logging.info(test_result.details)
        logging.info(f"{'-' * 80}\n\n")

    log_msg = '' if not log_file else f"\nSee log file for details: {log_file}"

    success = all(result.status == "SUCCEEDED" for result in test_results.values())
    if success:
        msg = f"SUCCESS: No differences found!{log_msg}"
        logging.info(msg)
    else:
        msg = f"ERROR: Differences were found!{log_msg}"
        logging.error(msg)

    if not args.log_to_terminal:
        print(msg)

    return success

def init_test_results(tests_to_diff, args):
    test_results = {}

    for test_name in tests_to_diff:
        baseline_path = Path(args.baseline_dir) / test_name
        test_path = Path(args.test_dir) / test_name

        baseline_found = baseline_path.is_dir()
        new_found = test_path.is_dir()

        # if test output is found for both baseline and new output
        if baseline_found and new_found:
            # if diffing inputs, init test results for TEST_NAME
            if args.diff_inputs:
                # default status is NOT RUN, so diff will be run for this test
                test_results[test_name] = TestResults()
                continue

            # otherwise init test results for each dated subdirectory

            # get dated subdirectories from both baseline and new output
            baseline_subdirs = _get_dated_subdirectories(baseline_path)
            test_subdirs = _get_dated_subdirectories(test_path)

            for subdir in baseline_subdirs.union(test_subdirs):
                # init test results for TEST_NAME/YYYYMMDDHH
                subdir_name = f"{test_name}/{subdir}"
                test_results[subdir_name] = TestResults()

                # mark tests as failed if dated subdirectory found in one but not the other
                if subdir in baseline_subdirs - test_subdirs:
                    test_results[subdir_name].status = 'FAILED (not in new output)'
                elif subdir in test_subdirs - baseline_subdirs:
                    test_results[subdir_name].status = 'FAILED (not in baseline output)'
                # if dated subdirectory found in both, leave status as NOT RUN to run diff

            continue

        # if test is not found in either baseline or new output, set status to failed
        test_results[test_name] = TestResults()

        if not baseline_found and not new_found:
            test_results[test_name].status = 'FAILED (not in either output)'
        elif baseline_found:
            test_results[test_name].status = 'FAILED (not in new output)'
        else:
            test_results[test_name].status = 'FAILED (not in baseline)'

    return test_results

def _get_dated_subdirectories(the_path):
    return set([x.name for x in the_path.iterdir() if x.is_dir() and x.name.isdigit()])

def read_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run difference tests")
    parser.add_argument("test_dir",
                        help="Directory with test output data to compare to baseline")
    parser.add_argument("--regression_dir", default=DEFAULT_REGRESSION_DIR,
                        help=f"Directory containing regression test output (default: {DEFAULT_REGRESSION_DIR})")
    parser.add_argument("--metplus",
                        help="Directory of METplus repo to get diff_util.py (default: regression_dir/METplus)")
    parser.add_argument("--baseline_dir",
                        help="Directory with baseline data to use for comparison (default: regression_dir/output.baseline)")
    parser.add_argument("--diff_inputs", action="store_true",
                        help="If set, run the diff utility on each output directory, which includes the input observation files.")
    parser.add_argument("--log_dir",
                        help="Directory where the log file should be saved (default: regression_dir)")
    parser.add_argument("--log_to_terminal", action="store_true",
                        help="If set, log to the terminal (standard output) instead of a file")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Log information about files that were skipped or had no differences")
    parser.add_argument("-t", "--tests", type=str, nargs="*",default=["all"],
                        help="Defines tests to diff (default: all)."
                             " Matches format expected by run_we2e_tests.py script.")
    args = parser.parse_args()

    if not args.metplus:
        args.metplus = Path(args.regression_dir) / "METplus"
    if not args.baseline_dir:
        args.baseline_dir = Path(args.regression_dir) / "output.baseline"
    if not args.log_dir:
        args.log_dir = args.regression_dir

    return args

def setup_logging(args):
    log_file_path = None
    log_config = {
        "format": "%(message)s",
        "level": logging.INFO,
    }
    if args.log_to_terminal:
        # Route logs to stdout (terminal)
        print("Logging to terminal because --log_to_terminal was set.")
        log_config["stream"] = sys.stdout
    else:
        # Ensure the directory exists before writing to it
        Path(args.log_dir).mkdir(parents=True, exist_ok=True)
        log_file_path = Path(args.log_dir) / f"diff_WE2E_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        print(f"Logging to file: {log_file_path}")
        log_config["filename"] = str(log_file_path)
        log_config["filemode"] = "w"

    logging.basicConfig(**log_config)
    return log_file_path


if __name__ == "__main__":
    status = main()
    if not status:
        sys.exit(1)
