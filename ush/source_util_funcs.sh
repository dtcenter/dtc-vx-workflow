function source_util_funcs() {
#
#-----------------------------------------------------------------------
#
# Get the full path to the file in which this script/function is located 
# (scrfunc_fp), the name of that file (scrfunc_fn), and the directory in
# which the file is located (scrfunc_dir).
#
#-----------------------------------------------------------------------
#
  if [[ $(uname -s) == Darwin ]]; then
    local scrfunc_fp=$( greadlink -f "${BASH_SOURCE[0]}" )
  else
    local scrfunc_fp=$( readlink -f "${BASH_SOURCE[0]}" )
  fi
  local scrfunc_fn=$( basename "${scrfunc_fp}" )
  local scrfunc_dir=$( dirname "${scrfunc_fp}" )
#
#-----------------------------------------------------------------------
#
# Get the name of this function.
#
#-----------------------------------------------------------------------
#
  local func_name="${FUNCNAME[0]}"
#
#-----------------------------------------------------------------------
#
# Set necessary directory variables.
#
#-----------------------------------------------------------------------
#
  local USHdir="${scrfunc_dir}"
  local bashutils_dir="${USHdir}/bash_utils"
#
#-----------------------------------------------------------------------
#
# Source the file that defines MacOS-specific UNIX command-line
# utilities, that mimic the functionality of the GNU equivalents
#
#-----------------------------------------------------------------------
#
  . ${bashutils_dir}/define_macos_utilities.sh
#
#-----------------------------------------------------------------------
#
# Source the file containing the functions that print out messages.
#
#-----------------------------------------------------------------------
#
  . ${bashutils_dir}/print_msg.sh
#
#-----------------------------------------------------------------------
#
# Source the file that sources YAML files as if they were bash
#
#-----------------------------------------------------------------------
#
  . ${bashutils_dir}/source_yaml.sh
}
source_util_funcs


