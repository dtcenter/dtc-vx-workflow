#!/usr/bin/env bash
#
#-----------------------------------------------------------------------
#
# The J-Job script for checking the post output.
#
# Run-time environment variables:
#
#    HH
#    ENSMEM_INDX
#    GLOBAL_VAR_DEFNS_FP
#    YYMMDD
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
python $SCRIPTSdir/check_post_output.py ${VERBOSE_FLAG} \
  --config="${GLOBAL_VAR_DEFNS_FP}" \
  --cycle_date="${YYMMDD}${HH}" \
  ${ENSMEM_ARG} || \
print_err_msg_exit "\
Call to \"check_post_output.py\" from \"${scrfunc_fn}\" failed."

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
cycle_dir="$EXPTDIR/${YYMMDD}${HH}"
mkdir -p "${cycle_dir}"
touch "${cycle_dir}/post_files_exist_${ensmem_name}.txt"
