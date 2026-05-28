#!/bin/bash

###
# configuration/arguments
###

# top-level directory containing regression test output

regression_dir=/scratch3/BMC/dtc/George.Mccabe/dtc-vx-regression

# account to run jobs

account=dtc

# machine to run jobs

machine=ursa


# get current branch and latest commit to create sub-directory to run tests

branch=$(git rev-parse --abbrev-ref HEAD)
commit=$(git rev-parse HEAD | cut -c1-7)
sub_dir=${branch}.${commit}
test_dir=${regression_dir}/${sub_dir}

# error/exit if branch/commit directory already exists

if [[ -d ${test_dir} ]]; then
  echo "ERROR: Test dir already exists: ${test_dir}"
  echo "       Remove it to run"
  exit 1
fi

# create test directory

echo "Creating directory: ${test_dir}"
mkdir -p "${test_dir}"

# run the tests

echo "Running all WE2E tests in ${sub_dir}"

we2e_test_dir=${0%/*}

echo "Sourcing setup_conda.sh"
source "${we2e_test_dir}/../../setup_conda.sh"

module load rocoto

test_script=${we2e_test_dir}/run_we2e_tests.py
cmd="${test_script} --account ${account} --machine ${machine} --tests all --expt_basedir ${test_dir}"
echo "RUNNING: ${cmd}"
nohup bash -c "$cmd" &
