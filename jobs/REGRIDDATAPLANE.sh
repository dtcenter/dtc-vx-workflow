#!/usr/bin/env bash

#
#-----------------------------------------------------------------------
#
# This script runs the METplus RegridDataPlane tool for verification
#
# Run-time environment variables:
#
#    GLOBAL_VAR_DEFNS_FP
#    YYMMDD
#    HH
#    VERBOSE
#    FIELD_GROUP
#    OBTYPE
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
python $SCRIPTSdir/regriddataplane.py ${VERBOSE_FLAG} \
  --config="${GLOBAL_VAR_DEFNS_FP}" \
  --cycle_date="${YYMMDD}${HH}" \
  --field_group="${FIELD_GROUP}" \
  --obtype="${OBTYPE}"  || \
print_err_msg_exit "\
Call to \"regriddataplane.py\" from \"${scrfunc_fn}\" failed."

