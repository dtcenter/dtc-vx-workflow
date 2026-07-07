#!/usr/bin/env bash

#
#-----------------------------------------------------------------------
#
# The J-Job that runs METplus's GridStat or PointStat tool to perform
# verification on the ensemble frequencies/ probabilities of a specified
# field (or group of fields).
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
python $SCRIPTSdir/gridstat_or_pointstat_ensprob.py ${VERBOSE_FLAG} \
  --config="${GLOBAL_VAR_DEFNS_FP}" \
  --cycle_date="${YYMMDD}${HH}" \
  --field_group="${FIELD_GROUP}" \
  --obs_dir="${OBS_DIR}" \
  --obtype="${OBTYPE}" \
  --fcst_level="${FCST_LEVEL}" \
  --fcst_thresh="${FCST_THRESH}" \
  ${ACCUM_ARG} || \
print_err_msg_exit "\
Call to \"gridstat_or_pointstat_ensprob.py\" from \"${scrfunc_fn}\" failed."
