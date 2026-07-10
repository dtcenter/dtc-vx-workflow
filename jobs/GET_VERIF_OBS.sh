#!/usr/bin/env bash

#
#-----------------------------------------------------------------------
#
# The J-Job script that checks, pulls, and stages observation data for
# model verification.
#
# Run-time environment variables:
#
#    GLOBAL_VAR_DEFNS_FP
#
# Experiment variables
#
#  user:
#    SCRIPTSdir
#    USHdir
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
)
for sect in ${sections[*]} ; do
  source_yaml ${GLOBAL_VAR_DEFNS_FP} ${sect}
done
# Sets up PYTHONPATH and VERBOSE environment variables
. $USHdir/set_job_env.sh
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
cmd=(
  python3 "${SCRIPTSdir}/get_obs.py"
     ${VERBOSE_FLAG}
      --var_defns_path "${GLOBAL_VAR_DEFNS_FP}"
      --obtype "${OBTYPE}"
      --obs_day "${YYMMDD}"
)
echo "CALLING: ${cmd[*]}"
"${cmd[@]}" || print_err_msg_exit "Error calling get_obs.py"
#
#-----------------------------------------------------------------------
#
# Create flag file that indicates completion of task.  This is needed by
# the workflow.
#
#-----------------------------------------------------------------------
#
mkdir -p ${WFLOW_FLAG_FILES_DIR}
# ${VARNAME,,} converts contents of VARNAME to lowercase
file_bn="get_obs_${OBTYPE,,}"
touch "${WFLOW_FLAG_FILES_DIR}/${file_bn}_${YYMMDD}_complete.txt"

