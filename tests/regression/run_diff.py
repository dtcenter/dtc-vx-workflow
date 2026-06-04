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

@dataclass
class TestResults:
    success: bool = False
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
    #diff_util_script = Path(args.metplus_dir) / "metplus" / "util" / "diff_util.py"

    sys.path.insert(0, str(args.metplus_dir))
    from metplus.util import diff_util
    diff_util.SKIP_KEYWORDS = SKIP_KEYWORDS

    tests_baseline = [x.name for x in Path(args.baseline_dir).iterdir() if x.is_dir()]
    tests_new = [x.name for x in Path(args.test_dir).iterdir() if x.is_dir()]

    if not check_for_missing_tests(tests_baseline, tests_new):
        success = False

    test_results = {x: TestResults() for x in tests_new if x in tests_baseline}
    for test_name, test_result in test_results.items():
        print(f"Diffing {test_name}...")
        baseline_test = Path(args.baseline_dir) / test_name
        new_test = Path(args.test_dir) / test_name

        # create text stream to capture diff output for each test
        text_stream = io.StringIO()
        with redirect_stdout(text_stream):
            diff_files = diff_util.compare_dir(baseline_test, new_test, debug=True)

        # save detailed report of diff test
        test_result.details = text_stream.getvalue().strip()

        if not diff_files:
            #print(f"{test_name}: No differences found.")
            test_result.success = True
            continue

        #print(f"{test_name}: Differences found!")
        success = False

    print("SUMMARY:")
    for test_name, test_result in test_results.items():
        print(f"{test_name.ljust(65)}:  {'SUCCEEDED' if test_result.success else 'FAILED'}")

    if success:
        print("No differences found!")
    return success

def read_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run difference tests")
    parser.add_argument("test_dir",
                        help="Directory with test output data to compare to baseline")

    parser.add_argument("--metplus_dir", default=DEFAULT_METPLUS_DIR,
                        help=f"Directory of METplus repo to get diff_util.py (default: {DEFAULT_METPLUS_DIR})")
    parser.add_argument("--baseline_dir", default=DEFAULT_BASELINE_DIR,
                        help=f"Directory with baseline data to use for comparison (default: {DEFAULT_BASELINE_DIR})")

    args = parser.parse_args()
    return args

def check_for_missing_tests(baseline_tests, new_tests):
    # fail if there are any new tests that aren't in the baseline
    success = True
    not_in_baseline = [x for x in new_tests if x not in baseline_tests]
    if not_in_baseline:
        print(f"ERROR: The following tests are not in the baseline directory: {not_in_baseline}")
        success = False

    not_in_new = [x for x in baseline_tests if x not in new_tests]
    if not_in_new:
        print(f"ERROR: The following tests are not in the new directory: {not_in_new}")
        success = False

    return success

if __name__ == "__main__":
    main()