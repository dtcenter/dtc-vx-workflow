#!/usr/bin/env bash

#
#-----------------------------------------------------------------------
#
# This script runs the METplus GridStat or PointStat tool for
# deterministic verification.
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
VERBOSE_FLAG=""
if [ "${VERBOSE}" = "True" ]; then
  VERBOSE_FLAG="--verbose"
fi
if [ ! -z "${ACCUM_HH}" ]; then
  ACCUM_ARG="--accum_hh=${ACCUM_HH}"
fi
python $SCRIPTSdir/gridstat_or_pointstat.py ${VERBOSE_FLAG} ${ACCUM_ARG} \
  --config="${GLOBAL_VAR_DEFNS_FP}" \
  --cycle_date="${YYMMDD}${HH}" \
  --ensmem_index="${ENSMEM_INDX}" \
  --field_group="${FIELD_GROUP}" \
  --fcst_level="${FCST_LEVEL}" \
  --fcst_thresh="${FCST_THRESH}" \
  --obtype="${OBTYPE}" \
  --obs_dir="${OBS_DIR}" || \
print_err_msg_exit "\
Call to \"gridstat_or_pointstat.py\" from \"${scrfunc_fn}\" failed."

