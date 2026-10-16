#!/usr/bin/env bash

#
#-----------------------------------------------------------------------
#
# This script runs the METplus Point2Grid tool for verification
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

printf "
========================================================================
Entering script:  \"${scrfunc_fn}\"
In directory:     \"${scrfunc_dir}\"
========================================================================"
#
# Call the run script
#
python $SCRIPTSdir/point2grid.py ${VERBOSE_FLAG} \
  --config="${GLOBAL_VAR_DEFNS_FP}" \
  --cycle_date="${YYMMDD}${HH}" \
  --field_group="${FIELD_GROUP}" \
  --fcst_level="${FCST_LEVEL}" \
  --obtype="${OBTYPE}" \
  --obs_dir="${OBS_DIR}" || \
print_err_msg_exit "\
Call to \"point2grid.py\" from \"${scrfunc_fn}\" failed."

