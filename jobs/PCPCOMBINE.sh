#!/usr/bin/env bash

#
#-----------------------------------------------------------------------
#
# The J-job that runs the MET/METplus PcpCombine tool on hourly
# accumulated precipitation (APCP) data to obtain APCP for multi-hour
# accumulation periods.  The data can be from CCPA observations or a
# focrecast.
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
. $USHdir/job_preamble.sh
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
$SCRIPTSdir/pcpcombine.sh || \
print_err_msg_exit "\
Call to \"pcpcombine.sh\" from \"${scrfunc_fn}\" failed."
#
#-----------------------------------------------------------------------
#
# Run job postamble.
#
#-----------------------------------------------------------------------
#
job_postamble

