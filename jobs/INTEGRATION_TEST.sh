#!/usr/bin/env bash


#
#-----------------------------------------------------------------------
#
# This J-Job script runs a set of tests at the end of WE2E tests.
#
# Run-time environment variables:
#
#    GLOBAL_VAR_DEFNS_FP
#    FCST_DIR
#    SLASH_ENSMEM_SUBDIR
#
# Experiment variables
#
#  user:
#    RUN_ENV
#    SCRIPTSdir
#    USHdir
#
#  workflow:
#    FCST_LEN_HRS
#
#-----------------------------------------------------------------------
#

#
#-----------------------------------------------------------------------
#
# Source the conda setup and variable definitions files
#
#-----------------------------------------------------------------------
#
. $USHdir/../setup_conda.sh
. $USHdir/source_util_funcs.sh
sections=(
  user
  workflow
  task_integration_test.envvars
)
for sect in ${sections[*]} ; do
  source_yaml ${GLOBAL_VAR_DEFNS_FP} ${sect}
done

#
#-----------------------------------------------------------------------
#
# Get the full path to the file in which this script/function is located 
# (scrfunc_fp), the name of that file (scrfunc_fn), and the directory in
# which the file is located (scrfunc_dir).
#
#-----------------------------------------------------------------------
#
scrfunc_fp=$( $READLINK -f "${BASH_SOURCE[0]}" )
scrfunc_fn=$( basename "${scrfunc_fp}" )
scrfunc_dir=$( dirname "${scrfunc_fp}" )

print_info_msg "
========================================================================
Entering script:  \"${scrfunc_fn}\"
In directory:     \"${scrfunc_dir}\"
========================================================================"
#
# Call the run script
#
$SCRIPTSdir/integration_test.py \
           --fcst_dir="${FCST_DIR}" \
           --fcst_len=${FCST_LEN_HRS} || \
print_err_msg_exit "\
Call to script \"integration_test.py\" from \"${scrfunc_fn}\" failed."
