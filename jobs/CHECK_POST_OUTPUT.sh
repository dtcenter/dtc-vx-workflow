#!/usr/bin/env bash
set -x
#
#-----------------------------------------------------------------------
#
# The J-Job script for checking the post output.
#
# Run-time environment variables:
#
#    cyc
#    ENSMEM_INDX
#    GLOBAL_VAR_DEFNS_FP
#    PDY
#
# Experiment variables
#
#  user:
#    SCRIPTSdir
#    USHdir
#
#  workflow:
#    EXPTDIR
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
$SCRIPTSdir/check_post_output.sh || \
print_err_msg_exit "\
Call to script \"check_post_output.sh\" from \"${scrfunc_fn}\" failed."
#
#-----------------------------------------------------------------------
#
# Create a flag file to make rocoto aware that the check_post_output task
# has successfully completed (so that other tasks that depend on it can
# be launched).  
#
#-----------------------------------------------------------------------
#
ensmem_name="mem${ENSMEM_INDX}"
cycle_dir="$EXPTDIR/${PDY}${cyc}"
mkdir -p "${cycle_dir}"
touch "${cycle_dir}/post_files_exist_${ensmem_name}.txt"
