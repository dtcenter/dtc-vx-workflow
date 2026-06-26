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

@dataclass
class TestResults:
    status: str = NOT_RUN
    details: str = ""

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
]

def main():
    args = read_args()

    # set up logging
    setup_logging(args)

    if not Path(args.metplus).exists():
        print(f"ERROR: METplus directory does not exist: {args.metplus}")
        sys.exit(1)

    success = True

    sys.path.insert(0, str(args.metplus))
    from metplus.util import diff_util
    diff_util.SKIP_KEYWORDS = SKIP_KEYWORDS

    tests_baseline = get_test_paths(args.baseline, not args.diff_all_files)
    tests_new = get_test_paths(args.test_dir, not args.diff_all_files)

    all_tests = list(set(tests_baseline).union(tests_new))
    test_results = {x: TestResults() for x in all_tests}

    # set tests that are not found in either baseline or new output to failed
    not_in_baseline = [x for x in tests_new if x not in tests_baseline]
    not_in_new = [x for x in tests_baseline if x not in tests_new]
    for test_name in not_in_baseline:
        test_results[test_name].status = 'FAILED (not in baseline)'
        success = False
    for test_name in not_in_new:
        test_results[test_name].status = 'FAILED (not in new output)'
        success = False

    for test_name, test_result in test_results.items():
        if test_result.status != NOT_RUN:
            continue

        print(f"Diffing {test_name}...")
        baseline_test = Path(args.baseline) / test_name
        new_test = Path(args.test_dir) / test_name

        # create text stream to capture diff output for each test
        text_stream = io.StringIO()
        with redirect_stdout(text_stream):
            diff_files = diff_util.compare_dir(str(baseline_test), str(new_test), debug=True)

        # save detailed report of diff test
        test_result.details = text_stream.getvalue().strip()

        if not diff_files:
            test_result.status = 'SUCCEEDED'
            continue

        test_result.status = 'FAILED'
        success = False

    logging.info("SUMMARY:")
    for test_name, test_result in test_results.items():
        logging.info(f"{test_name.ljust(65)}:  {test_result.status}")

    logging.info("DETAILS:")
    for test_name, test_result in test_results.items():
        logging.info(f"{'-' * 80}\n{test_name}: {test_result.status}\n{'-' * 80}")
        logging.info(test_result.details)
        logging.info(f"{'-' * 80}\n\n")

    if success:
        msg = "SUCCESS: No differences found!"
        logging.info(msg)
    else:
        msg = "ERROR: Differences were found!"
        logging.error(msg)

    if not args.log_to_terminal:
        print(msg)

    return success

def read_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run difference tests")
    parser.add_argument("test_dir",
                        help="Directory with test output data to compare to baseline")
    parser.add_argument("--regression_dir", default=DEFAULT_REGRESSION_DIR,
                        help=f"Directory containing regression test output (default: {DEFAULT_REGRESSION_DIR})")
    parser.add_argument("--metplus",
                        help="Directory of METplus repo to get diff_util.py (default: regression_dir/METplus)")
    parser.add_argument("--baseline",
                        help="Directory with baseline data to use for comparison (default: regression_dir/output.baseline)")
    parser.add_argument("--diff_all_files", action="store_true",)
    parser.add_argument("--log_dir",
                        help="Directory where the log file should be saved (default: regression_dir)")
    parser.add_argument("--log_to_terminal", action="store_true",
                        help="If set, log to the terminal (standard output) instead of a file")

    args = parser.parse_args()

    if not args.metplus:
        args.metplus = Path(args.regression_dir) / "METplus"
    if not args.baseline:
        args.baseline = Path(args.regression_dir) / "output.baseline"
    if not args.log_dir:
        args.log_dir = args.regression_dir

    return args

def setup_logging(args):
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

def get_test_paths(base_path, get_dated=True):
    paths = []
    # Loop through the main test directories (e.g., TEST_NAME)
    for test_dir in Path(base_path).iterdir():
        if not test_dir.is_dir():
            continue

        has_date_subdirs = False

        if get_dated:
            # Look for numeric subdirectories inside the test directory
            for sub_dir in test_dir.iterdir():
                if sub_dir.is_dir() and sub_dir.name.isdigit():
                    # Store as 'TEST_NAME/202602010000'
                    paths.append(f"{test_dir.name}/{sub_dir.name}")
                    has_date_subdirs = True

        # Fallback if get_dated is False or no numeric subdirs were found
        if not has_date_subdirs:
            paths.append(test_dir.name)

    return paths

if __name__ == "__main__":
    status = main()
    if not status:
        sys.exit(1)
