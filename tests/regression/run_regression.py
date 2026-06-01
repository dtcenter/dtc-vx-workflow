#!/usr/bin/env python3

import argparse
import subprocess
import sys
import shlex
from argparse import Namespace
from pathlib import Path

WORKFLOW_REPO = "NCAR/dtc-vx-workflow"
DEFAULT_REGRESSION_DIR = "/scratch3/BMC/dtc/dtc-vx-workflow_testing"

def run_git_command(command):
    """Run a git command and return its output."""
    try:
        result = subprocess.run(shlex.split(command), capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command {command}: {e.stderr}")
        sys.exit(1)

def main():

    args = read_args()

    print(f"Regression directory: {args.regression_dir}")

    branch_or_pr_dir = args.branch if args.branch else f"pr_{args.pr}"
    branch_or_pr_dir = Path(args.regression_dir) / branch_or_pr_dir
    workflow_repo_dir = Path(branch_or_pr_dir) / WORKFLOW_REPO.split('/')[-1]

    setup_repo_dir(args, workflow_repo_dir)

    # Get latest commit to create directory for test output
    commit = run_git_command(f"git -C {workflow_repo_dir} rev-parse HEAD")[:7]

    output_path = Path(branch_or_pr_dir) / f"output.{commit}"

    # Error/exit if branch/commit directory already exists
    if output_path.is_dir():
        print(f"WARNING: Test dir already exists: {output_path}")
        print("         Remove it to run")
        sys.exit(0)

    # Create test directory
    print(f"Creating directory: {output_path}")
    output_path.mkdir(parents=True, exist_ok=True)

    launch_tests(args, workflow_repo_dir, output_path)


def read_args() -> Namespace:
    parser = argparse.ArgumentParser(description="Run regression tests")
    parser.add_argument("--branch", help="Branch to run tests for.")
    parser.add_argument("--pr", help="Pull request to run tests for")
    parser.add_argument("--account", required=True, help="Account to run jobs")
    parser.add_argument("--machine", required=True, help="Machine to run jobs")
    parser.add_argument("--regression_dir", default=DEFAULT_REGRESSION_DIR,
                        help=f"Directory to run regression tests (default: {DEFAULT_REGRESSION_DIR})")
    parser.add_argument("--clone_https", action="store_true",
                        help="Clone via https instead of ssh", )

    args = parser.parse_args()

    # check if branch or pr is specified, but not both
    if (args.branch and args.pr) or (not args.branch and not args.pr):
        print("ERROR: Must specify either --branch or --pr, but not both")
        sys.exit(1)
    return args


def setup_repo_dir(args: Namespace, workflow_repo_dir: Path):
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


def launch_tests(args: Namespace, workflow_repo_dir: Path, output_path: Path):
    print(f"Running all WE2E tests in {Path(output_path.parent.name) / output_path.name}")

    # Determine paths relative to the workflow repo directory
    test_script = Path(workflow_repo_dir) / "tests" / "WE2E" / "run_we2e_tests.py"

    # Command to run the tests
    cmd = f"{test_script} --account {args.account} --machine {args.machine} --tests all --expt_basedir {output_path}"

    # Replicate shell-specific setup and background execution
    # Combine the environment setup and the test command into a single bash call
    # Run via nohup in the background
    setup_conda_path = Path(workflow_repo_dir) / "setup_conda.sh"
    full_cmd = f"source {setup_conda_path} && module load rocoto && {cmd}"

    print("Sourcing setup_conda.sh")
    print(f"RUNNING: {cmd}")
    print("Launching in background with nohup -- follow nohup.out for output")

    # Execute in background with nohup
    try:
        # Construct the final command to be passed to bash
        final_shell_cmd = f"nohup bash -c '{full_cmd}' &"
        subprocess.Popen(final_shell_cmd, shell=True)
    except Exception as e:
        print(f"Failed to launch test command: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
