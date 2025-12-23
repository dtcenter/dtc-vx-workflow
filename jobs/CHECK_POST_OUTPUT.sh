#!/usr/bin/env bash

#
#-----------------------------------------------------------------------
#
# The J-Job script for checking the post output.
#
# Run-time environment variables:
#
#    CDATE
#    ENSMEM_INDX
#    GLOBAL_VAR_DEFNS_FP
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
. $USHdir/job_preamble.sh
#
#-----------------------------------------------------------------------
#
# Save current shell options (in a global array).  Then set new options
# for this script/function.
#
#-----------------------------------------------------------------------
#
{ save_shell_opts; . $USHdir/preamble.sh; } > /dev/null 2>&1
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
echo "shell_opts_array=${shell_opts_array}"
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
cycle_dir="$EXPTDIR/$CDATE"
mkdir -p "${cycle_dir}"
touch "${cycle_dir}/post_files_exist_${ensmem_name}.txt"
#
#-----------------------------------------------------------------------
#
# Run job postamble.
#
#-----------------------------------------------------------------------
#
job_postamble
#
#-----------------------------------------------------------------------
#
# Restore the shell options saved at the beginning of this script/func-
# tion.
#
#-----------------------------------------------------------------------
#
{ restore_shell_opts; } > /dev/null 2>&1
