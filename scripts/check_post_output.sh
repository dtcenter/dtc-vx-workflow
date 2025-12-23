#!/usr/bin/env bash
set -x
#
#-----------------------------------------------------------------------
#
# The ex-script for checking the post output.
#
# Run-time environment variables:
#
#    ACCUM_HH
#    ENSMEM_INDX
#    HH
#    GLOBAL_VAR_DEFNS_FP
#    METPLUS_ROOT (used by ush/set_leadhrs.py)
#    YYMMDD
#
# Experiment variables
#
#  user:
#    USHdir
#
#  workflow:
#    FCST_LEN_HRS
#
#  global:
#    DO_ENSEMBLE
#    ENS_TIME_LAG_HRS
#
#  verification:
#    FCST_FN_TEMPLATE
#    FCST_SUBDIR_TEMPLATE
#    NUM_MISSING_FCST_FILES_MAX
#    VX_FCST_INPUT_BASEDIR
#    VX_NDIGITS_ENSMEM_NAMES
#
#-----------------------------------------------------------------------
#

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
  global
  verification
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
#
#-----------------------------------------------------------------------
#
# Print message indicating entry into script.
#
#-----------------------------------------------------------------------
#
print_info_msg "
========================================================================
Entering script:  \"${scrfunc_fn}\"
In directory:     \"${scrfunc_dir}\"

This is the ex-script for the task that checks that no more than
NUM_MISSING_FCST_FILES_MAX of each forecast's (ensemble member's) post-
processed output files are missing.
========================================================================"
#
#-----------------------------------------------------------------------
#
# Get the time lag for the current ensemble member.
#
#-----------------------------------------------------------------------
#
i="0"
if [[ "${DO_ENSEMBLE}" == "True" ]]; then
  i=$( bc -l <<< "${ENSMEM_INDX}-1" )
fi
time_lag=$( bc -l <<< "${ENS_TIME_LAG_HRS[$i]}*3600" )
#
#-----------------------------------------------------------------------
#
# Check to ensure that all the expected post-processed forecast output
# files are present on disk.  This is done by the set_leadhrs function
# below.
#
#-----------------------------------------------------------------------
#
ensmem_indx=$(printf "%0${VX_NDIGITS_ENSMEM_NAMES}d" $(( 10#${ENSMEM_INDX})))
ensmem_name="mem${ensmem_indx}"
FCST_INPUT_FN_TEMPLATE=$( eval echo ${FCST_SUBDIR_TEMPLATE:+${FCST_SUBDIR_TEMPLATE}/}${FCST_FN_TEMPLATE} )

FHR_LIST=$( python3 $USHdir/set_leadhrs.py \
  --date_init="${YYMMDD}${HH}" \
  --lhr_min="0" \
  --lhr_max="${FCST_LEN_HRS}" \
  --lhr_intvl="${VX_FCST_OUTPUT_INTVL_HRS}" \
  --base_dir="${VX_FCST_INPUT_BASEDIR}" \
  --fn_template="${FCST_INPUT_FN_TEMPLATE}" \
  --num_missing_files_max="${NUM_MISSING_FCST_FILES_MAX}" \
  --time_lag="${time_lag%.*}") || \
print_err_msg_exit "Call to set_leadhrs.py failed with return code: $?"
#
#-----------------------------------------------------------------------
#
# Print message indicating successful completion of script.
#
#-----------------------------------------------------------------------
#
print_info_msg "
========================================================================
Done checking for existence of post-processed files for ensemble member ${ENSMEM_INDX}.

Exiting script:  \"${scrfunc_fn}\"
In directory:    \"${scrfunc_dir}\"
========================================================================"
