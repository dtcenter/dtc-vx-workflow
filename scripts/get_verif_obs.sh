#!/usr/bin/env bash

#
#-----------------------------------------------------------------------
#
# The ex-script that checks, pulls, and stages observation data for
# model verification.
#
# Run-time environment variables:
#
#    FHR
#    GLOBAL_VAR_DEFNS_FP
#    OBS_DIR
#    OBTYPE
#    VAR
#    YYMMDD
#
# Experiment variables
#
#   user:
#    USHdir
#    PARMdir
#
#-----------------------------------------------------------------------

#
#-----------------------------------------------------------------------
#
# Source the variable definitions file and the bash utility functions.
#
#-----------------------------------------------------------------------
#
. $USHdir/source_util_funcs.sh
sections=(
  user
  workflow
  verification
)
for sect in ${sections[*]} ; do
  source_yaml ${GLOBAL_VAR_DEFNS_FP} ${sect}
done
#
#-----------------------------------------------------------------------
#
# Make sure the obs type is valid.  Then call a python script to check
# for the presence of obs files on disk and get them if needed.
#
#-----------------------------------------------------------------------
#
LOGLEVEL="INFO"
echo "DEBUG=$DEBUG"
if [ "${DEBUG}" = "True" ]; then
  LOGLEVEL="DEBUG"
fi
echo "LOGLEVEL=$LOGLEVEL"

cmd="\
python3 -u ${USHdir}/get_obs.py \
--var_defns_path "${GLOBAL_VAR_DEFNS_FP}" \
--obtype ${OBTYPE} \
--log_level ${LOGLEVEL} \
--obs_day ${YYMMDD}"
print_info_msg "
CALLING: ${cmd}"
${cmd} || print_err_msg_exit "Error calling get_obs.py"
#
#-----------------------------------------------------------------------
#
# Create flag file that indicates completion of task.  This is needed by
# the workflow.
#
#-----------------------------------------------------------------------
#
mkdir -p ${WFLOW_FLAG_FILES_DIR}
file_bn="get_obs_$(echo_lowercase ${OBTYPE})"
touch "${WFLOW_FLAG_FILES_DIR}/${file_bn}_${YYMMDD}_complete.txt"

