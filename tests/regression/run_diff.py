#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path
import io
from contextlib import redirect_stdout
from dataclasses import dataclass

DEFAULT_REGRESSION_DIR = "/scratch3/BMC/dtc/dtc-vx-workflow_testing"
DEFAULT_METPLUS_DIR = Path(DEFAULT_REGRESSION_DIR) / "METplus"
DEFAULT_BASELINE_DIR = Path(DEFAULT_REGRESSION_DIR) / "baseline"

NOT_RUN = "NOT RUN"

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
    if not Path(args.metplus_dir).exists():
        print(f"ERROR: METplus directory does not exist: {args.metplus_dir}")
        sys.exit(1)

    success = True

    sys.path.insert(0, str(args.metplus_dir))
    from metplus.util import diff_util
    diff_util.SKIP_KEYWORDS = SKIP_KEYWORDS

    tests_baseline = get_test_paths(args.baseline_dir, not args.diff_all_files)
    tests_new = get_test_paths(args.test_dir, not args.diff_all_files)

    #tests_baseline = [x.name for x in Path(args.baseline_dir).iterdir() if x.is_dir()]
    #tests_new = [x.name for x in Path(args.test_dir).iterdir() if x.is_dir()]

    all_tests = list(set(tests_baseline) & set(tests_new))
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
        baseline_test = Path(args.baseline_dir) / test_name
        new_test = Path(args.test_dir) / test_name

        # create text stream to capture diff output for each test
        text_stream = io.StringIO()
        with redirect_stdout(text_stream):
            diff_files = diff_util.compare_dir(str(baseline_test), str(new_test), debug=True)

        # save detailed report of diff test
        test_result.details = text_stream.getvalue().strip()

        if not diff_files:
            test_result.success = True
            continue

        success = False

    print("SUMMARY:")
    for test_name, test_result in test_results.items():
        print(f"{test_name.ljust(65)}:  {'SUCCEEDED' if test_result.success else 'FAILED'}")

    return success

def read_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run difference tests")
    parser.add_argument("test_dir",
                        help="Directory with test output data to compare to baseline")

    parser.add_argument("--metplus_dir", default=DEFAULT_METPLUS_DIR,
                        help=f"Directory of METplus repo to get diff_util.py (default: {DEFAULT_METPLUS_DIR})")
    parser.add_argument("--baseline_dir", default=DEFAULT_BASELINE_DIR,
                        help=f"Directory with baseline data to use for comparison (default: {DEFAULT_BASELINE_DIR})")
    parser.add_argument("--diff_all_files", action="store_true",)
    args = parser.parse_args()
    return args


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
    result = main()
    if result:
        print("No differences found!")
