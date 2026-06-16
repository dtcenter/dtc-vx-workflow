#!/usr/bin/env python3

import argparse
import subprocess
import sys
import shlex
from pathlib import Path

BASELINE_COMMIT = "758ea56"
#BASELINE_COMMIT = "84b78ac3"
BASELINE_BRANCH = "develop"

WORKFLOW_REPO = "dtcenter/dtc-vx-workflow"
DEFAULT_REGRESSION_DIR = "/scratch3/BMC/dtc/dtc-vx-workflow_testing"

def main():

    args = read_args()

    print(f"Regression directory: {args.regression_dir}")

    branch_or_pr_dir = f"pr_{args.pr}" if args.pr else args.branch
    branch_or_pr_dir = Path(args.regression_dir) / branch_or_pr_dir
    workflow_repo_dir = Path(branch_or_pr_dir) / WORKFLOW_REPO.split('/')[-1]

    setup_repo_dir(args, workflow_repo_dir)

    # create directory for test output
    # get explicit commit if specified, otherwise get latest commit
    if args.commit:
        commit = args.commit
    else:
        commit = run_git_command(f"git -C {workflow_repo_dir} rev-parse HEAD")[:7]

    output_path = Path(branch_or_pr_dir) / f"output.{commit}"

    # Error/exit if branch/commit directory already exists
    if output_path.is_dir():
        print(f"WARNING: Test dir already exists: {output_path}")
        print("         Remove it to run")
    else:

        # Create test directory
        print(f"Creating directory: {output_path}")
        output_path.mkdir(parents=True, exist_ok=True)

        launch_tests(args, workflow_repo_dir, output_path)

    # if running baseline, update symbolic link for baseline output dir
    if args.baseline:
        baseline_dir = Path(args.regression_dir) / "output.baseline"
        print(f"Updating symbolic link output.baseline to point to {output_path}")

        # remove link if it exists already
        if baseline_dir.is_symlink():
            print(f"Removing existing symbolic link: {baseline_dir}")
            baseline_dir.unlink()

        baseline_dir.symlink_to(output_path, target_is_directory=True)

def read_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run regression tests")
    parser.add_argument("--baseline", action="store_true",
                        help="Run tests for baseline commit. Ignore branch/pr/commit args.")
    parser.add_argument("--branch", help="Branch to run tests for.")
    parser.add_argument("--pr", help="Pull request to run tests for")
    parser.add_argument("--commit", help="Specific commit to run tests for")
    parser.add_argument("--account", required=True, help="Account to run jobs")
    parser.add_argument("--machine", required=True, help="Machine to run jobs")
    parser.add_argument("--regression_dir", default=DEFAULT_REGRESSION_DIR,
                        help=f"Directory to run regression tests (default: {DEFAULT_REGRESSION_DIR})")
    parser.add_argument("--clone_https", action="store_true",
                        help="Clone via https instead of ssh", )

    args = parser.parse_args()

    # if baseline is requested, set branch and commit to baseline values and unset pr arg

    if args.baseline:
        args.branch = BASELINE_BRANCH
        args.commit = BASELINE_COMMIT
        args.pr = None

    # error if pr is requested and a branch or commit is also requested

    if args.pr and (args.branch or args.commit):
        print("ERROR: Cannot specify --branch or --commit with --pr")
        sys.exit(1)

    return args

def run_git_command(command):
    """Run a git command and return its output."""
    try:
        result = subprocess.run(shlex.split(command), capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command {command}: {e.stderr}")
        sys.exit(1)

def setup_repo_dir(args: argparse.Namespace, workflow_repo_dir: Path):
    if not workflow_repo_dir.exists():
        # Clone workflow repo
        repo_loc = f"https://github.com/{WORKFLOW_REPO}" if args.clone_https else f"git@github.com:{WORKFLOW_REPO}"
        run_git_command(f"git clone {repo_loc} {workflow_repo_dir}")

        # check out the branch or PR merge commit
        if args.branch:
            run_git_command(f"git -C {workflow_repo_dir} checkout {args.branch}")
        else:
            merge_commit_id = f"refs/pull/{args.pr}/merge"
            run_git_command(f"git -C {workflow_repo_dir} fetch origin {merge_commit_id}")
            run_git_command(f"git -C {workflow_repo_dir} checkout {merge_commit_id}")

    # pull latest changes
    run_git_command(f"git -C {workflow_repo_dir} pull")

    # check out specific commit if specified
    if args.commit:
        run_git_command(f"git -C {workflow_repo_dir} checkout {args.commit}")

def launch_tests(args: argparse.Namespace, workflow_repo_dir: Path, output_path: Path):
    print(f"Running all WE2E tests in {Path(output_path.parent.name) / output_path.name}")

    # Determine paths relative to the workflow repo directory

    we2e_test_dir = workflow_repo_dir / "tests" / "WE2E"
    test_script = we2e_test_dir / "run_we2e_tests.py"

    # Commands to set up conda and run the tests

    cmd = (
        f"source {workflow_repo_dir}/setup_conda.sh &&"
        f" {test_script} --account {args.account} --machine {args.machine}"
        f" --tests all --expt_basedir {output_path}"
    )

    print(f"RUNNING: {cmd}")
    print(f"CWD: {we2e_test_dir}")
    print("Launching in background with nohup")
    print(f"Follow {we2e_test_dir}/nohup.out for output", flush=True)

    try:
        # run setup_conda.sh and end-to-end test script

        subprocess.Popen(f"nohup bash -c '{cmd}' &", shell=True, cwd=we2e_test_dir)

    except Exception as e:
        print(f"Failed to launch test command: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
