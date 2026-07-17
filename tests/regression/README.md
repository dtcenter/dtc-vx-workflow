# Regression Testing

## Initializing the Test Environment

1. Create regression directory

Determine a directory to store the test output, e.g. `/scratch3/BMC/dtc/dtc-vx-workflow_testing`.
This directory will be used to store the output of the end-to-end test runs
and the METplus code that contains the diff utility script.

Create the directory if it does not already exist.

```
regression_dir=/scratch3/BMC/dtc/dtc-vx-workflow_testing
mkdir -p ${regression_dir}
```

To enable other users to run the tests in this directory,
ensure that the **{regression_dir}** directory has group read/write permissions.

```
chmod g+w ${regression_dir}
```

2. Get METplus

Navigate to the test directory and clone the METplus repository,
using the develop branch.

```
regression_dir=/scratch3/BMC/dtc/dtc-vx-workflow_testing
cd ${regression_dir}
git clone git@github.com:dtcenter/METplus --branch develop
```

3. Create the Baseline Output

Run the regression test script on the develop branch of `dtc-vx-workflow`
to establish a baseline output dataset to compare to the output from other
branches and/or pull requests.
Follow the instructions under the **Generating/Updating the Baseline Output** section.

## Running the Tests

Tests can be run for a branch, pull request, or a specific commit, e.g. the baseline commit.
The `run_regression.py` script will submit a workflow for each end-to-end test case.
In the **{regression_dir}** directory,
a directory will be created named after the branch or pull request. 
In that directory, the **dtc-vx-workflow** repository will be cloned using
the branch or merge commit of the pull request. The end-to-end test script
will be run from the **dtc-vx-workflow** directory.
The output will be written to a directory named **output.XXXXXXX** where
*XXXXXXX* is the latest commit has of the branch or pull request.
Subsequent runs will pull the latest changes from the branch or pull request
and rerun the tests, writing to a new **output.XXXXXXX** directory.

```text
{regression_dir}/
├── develop/
│   ├── dtc-vx-workflow/
│   ├── output.abcdef1/
│   └── output.2345678/
├── pr_10/
│   ├── dtc-vx-workflow/
│   ├── output.9abcdef/
│   └── output.1234567/
└── feature/add_HAFS_vx/
    ├── dtc-vx-workflow/
    └── output.b252ab7/
```

The script starts the end-to-end test script using nohup.
The full path to the nohup.out is printed to the screen.
Run `tail -f` on it to see the progress of the tests.

### Generating/Updating the Baseline Output

Calling the `run_regression.py` script with the `--baseline` argument will
run the end-to-end tests for the baseline commit and create a symbolic link
named **output.baseline** in the regression directory.
The baseline commit is stored in the `regression_baseline.py` file in the
**BASELINE_COMMIT** variable.

To update the baseline version, note the first 7 characters of the latest
commit on the develop branch after the changes that modify the output
have been merged.
Open the `regression_baseline.py` file and modify the value of the
**BASELINE_COMMIT** variable to the new commit hash.
**Be sure to commit the change to the develop branch of `dtc-vx-workflow`.**
If the output from the baseline commit has already been generated locally,
the script will skip the tests and update the symbolic link to the baseline commit.

```
account=dtc

machine=ursa
regression_dir=/scratch3/BMC/dtc/dtc-vx-workflow_testing

cd dtc-vx-workflow
python3 ./tests/regression/run_regression.py \
  --baseline \
  --account ${account} \
  --machine ${machine} \
  --regression_dir ${regression_dir}
```

### Running on a Branch

```
branch=develop
account=dtc

machine=ursa
regression_dir=/scratch3/BMC/dtc/dtc-vx-workflow_testing

cd dtc-vx-workflow
python3 ./tests/regression/run_regression.py \
  --branch ${branch} \
  --account ${account} \
  --machine ${machine} \
  --regression_dir ${regression_dir}
```

### Running on a Pull Request

The instructions for running on a pull request are nearly the same as for running on a branch.
The only difference is that the pull request number is specified using the `--pr` argument instead
of specifying the branch name using the `--branch` argument.

```
pr_number=10
account=dtc

machine=ursa
regression_dir=/scratch3/BMC/dtc/dtc-vx-workflow_testing

cd dtc-vx-workflow
python3 ./tests/regression/run_regression.py \
  --pr ${pr_number} \
  --account ${account} \
  --machine ${machine} \
  --regression_dir ${regression_dir}
```

### Running on a Subset of Tests

The `--tests` argument can be provided to the `run_regression.py` script
to define a subset of tests to run.
The format of the argument is the same as the `--tests` argument to the
`tests/WE2E/run_we2e_tests.py` script.
The default behavior is to pass `--tests all` to the `run_we2e_tests.py` script.

## Running the Diff Utility

To run the METplus diff utility, call the `run_diff.py` script,
passing the path to the output directory of the end-to-end tests.
By default, the output.baseline directory is used as the baseline.
You can override this by passing the `--baseline_dir` argument.
You can also override the location of METplus to use with the `--metplus` argument.

The default behavior is to run the diff utility on all files in the dated subdirectories
under the output directory, because these are assumed to contain the actual MET output.
The `--diff_inputs` argument can be added to run the diff utility on each
output directory, which includes the input observation files.
A list of keywords to skip workflow files are defined in the `run_diff.py`
script in the **SKIP_KEYWORDS** variable.

```
regression_dir=/scratch3/BMC/dtc/dtc-vx-workflow_testing
test_dir=${regression_dir}/feature/my_branch_name/output.abcdef1

cd dtc-vx-workflow
source ./setup_conda.sh vx_diff
python3 ./tests/regression/run_diff.py \
  ${test_dir} \
  --regression_dir ${regression_dir}
```
