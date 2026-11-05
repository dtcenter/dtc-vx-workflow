#!/bin/bash
#
# Checks whether, for each of the given obs days, the workflow flag file
# whose name is obtained by replacing the "*" in flag_file_pattern with
# that day's date (YYYYMMDD) exists in wflow_flag_files_dir.  This assumes
# that the flag files contain exactly the date of the obs day (with no
# hour) in place of the "*".  Exits with 0 if all of these flag files
# exist, 1 if any of them does not (the missing ones are listed on stderr),
# and 2 if the arguments are invalid.
#
# This script is called from the dependencies of rocoto tasks, which rocoto
# evaluates (one after another) each time the workflow is launched, e.g.
# every minute from cron.  It is written in bash rather than Python because
# it then runs quickly and does not depend on which Python is available
# outside of the workflow's conda environment:  the system Python may be
# missing or old on some platforms, and starting the conda environment's
# Python from a parallel file system can take up to about half a second.
#
# Usage:
#   check_flag_file_presence.sh <wflow_flag_files_dir> <flag_file_pattern> \
#     <obs_day> [<obs_day> ...]
#
# Example:
#   check_flag_file_presence.sh "/path/to/wflow_flag_files" \
#     "get_obs_ccpa_*_complete.txt" 20260201 20260202 20260205
#
if [ $# -lt 3 ]; then
  echo "Usage: $(basename "$0") <wflow_flag_files_dir> <flag_file_pattern> <obs_day> [<obs_day> ...]" >&2
  exit 2
fi

wflow_flag_files_dir=$1
flag_file_pattern=$2
shift 2

stars=${flag_file_pattern//[^*]/}
if [ ${#stars} -ne 1 ]; then
  echo "$(basename "$0"): flag_file_pattern must contain exactly one \"*\": ${flag_file_pattern}" >&2
  exit 2
fi

missing_flag_files=()
for obs_day in "$@"; do
  flag_file="${wflow_flag_files_dir}/${flag_file_pattern/\*/${obs_day}}"
  [ -e "${flag_file}" ] || missing_flag_files+=("${flag_file}")
done

if [ ${#missing_flag_files[@]} -gt 0 ]; then
  echo "Missing flag files: ${missing_flag_files[*]}" >&2
  exit 1
fi
exit 0
