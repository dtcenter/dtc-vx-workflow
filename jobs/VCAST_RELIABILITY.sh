#!/usr/bin/env bash

#
#-----------------------------------------------------------------------
#
# The J-Job that generates VCasT configuration files and runs VCasT to
# aggregate ensemble-probability reliability (PCT) statistics and plot
# reliability diagrams for a specified grid field group.
#
# Run-time environment variables:
#
#    GLOBAL_VAR_DEFNS_FP
#    FIELD_GROUP
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
#-----------------------------------------------------------------------
#
# Phase 1: generate the VCasT configuration YAMLs and a run manifest.
#
# This runs in the vx_workflow environment (activated by setup_conda.sh above), which provides
# uwtools. The run script only WRITES files; it does not invoke vcast, so it makes no assumption
# about the vcast environment being available. It writes one YAML per vcast invocation and a
# manifest listing them in the order they must run (aggregation first, then the plots that read
# its output).
#
#-----------------------------------------------------------------------
#
manifest=$( mktemp )
python $SCRIPTSdir/vcast_reliability.py ${VERBOSE_FLAG} \
  --config="${GLOBAL_VAR_DEFNS_FP}" \
  --field_group="${FIELD_GROUP}" \
  --manifest="${manifest}" || \
print_err_msg_exit "\
Call to \"vcast_reliability.py\" from \"${scrfunc_fn}\" failed."
#
#-----------------------------------------------------------------------
#
# Phase 2: activate the separate 'vcast' conda environment and run vcast on each generated YAML,
# in manifest order. We switch environments only now, so phase 1 never depends on the vcast
# environment existing.
#
#-----------------------------------------------------------------------
#
. $USHdir/../setup_conda.sh vcast

while IFS= read -r yml ; do
  [ -n "${yml}" ] || continue
  vcast "${yml}" || print_err_msg_exit "\
vcast failed on configuration file \"${yml}\" (from \"${scrfunc_fn}\")."
done < "${manifest}"

rm -f "${manifest}"
