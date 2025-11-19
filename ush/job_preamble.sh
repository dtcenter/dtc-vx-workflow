#!/usr/bin/env bash

set +u

#
#-----------------------------------------------------------------------
#
# If requested to share data with next task, override jobid
# When an argument exists with this script, a shared job id will be created.
#
#-----------------------------------------------------------------------
#
export share_pid=${WORKFLOW_ID}_${PDY}${cyc}
if [ $# -ne 0 ]; then
    export pid=$share_pid
    export jobid=${job}.${pid}
fi

#
#-----------------------------------------------------------------------
#
# Set NCO standard environment variables
#
#-----------------------------------------------------------------------
#
export envir="${envir:-${envir_default}}"
export NET="${NET:-${NET_default}}"
export RUN="${RUN:-${RUN_default}}"
export model_ver="${model_ver:-${model_ver_default}}"
export COMROOT="${COMROOT:-${PTMP}/${envir}/com}"
export DATAROOT="${DATAROOT:-${PTMP}/${envir}/tmp}"
export DCOMROOT="${DCOMROOT:-${PTMP}/${envir}/dcom}"
export DATA_SHARE="${DATA_SHARE:-${DATAROOT}/DATA_SHARE/${PDY}${cyc}}"

mkdir -p ${DATA_SHARE}

export DBNROOT="${DBNROOT:-${DBNROOT_default}}"
export SENDECF="${SENDECF:-${SENDECF_default}}"
export SENDDBN="${SENDDBN:-${SENDDBN_default}}"
export SENDDBN_NTC="${SENDDBN_NTC:-${SENDDBN_NTC_default}}"
export SENDCOM="${SENDCOM:-${SENDCOM_default}}"
export SENDWEB="${SENDWEB:-${SENDWEB_default}}"
export KEEPDATA="${KEEPDATA:-${KEEPDATA_default}}"
export MAILTO="${MAILTO:-${MAILTO_default}}"
export MAILCC="${MAILCC:-${MAILCC_default}}"

  export COMIN="${EXPTDIR}/${PDY}${cyc}"
  export COMOUT="${EXPTDIR}/${PDY}${cyc}"
  export COMINm1="${EXPTDIR}/${PDYm1}${cyc}"
export COMOUTwmo="${COMOUTwmo:-${COMOUT}/wmo}"

#
#-----------------------------------------------------------------------
#
# Set cycle and ensemble member names in file/diectory names
#
#-----------------------------------------------------------------------
#
if [ ${subcyc:-0} -ne 0 ]; then
  export cycle="t${cyc}${subcyc}z"
else
  export cycle="t${cyc}z"
fi

    export dot_ensmem=
#
#-----------------------------------------------------------------------
#
# Run setpdy to initialize PDYm and PDYp variables
#
#-----------------------------------------------------------------------
#
    export PDYm1=$( $DATE_UTIL --date "${PDY} -1 day" "+%Y%m%d" )
    export PDYm2=$( $DATE_UTIL --date "${PDY} -2 day" "+%Y%m%d" )
    export PDYm3=$( $DATE_UTIL --date "${PDY} -3 day" "+%Y%m%d" )
export CDATE=${PDY}${cyc}
#
#-----------------------------------------------------------------------
#
# Set pgmout and pgmerr files
#
#-----------------------------------------------------------------------
#
    export pgmout=
    export pgmerr=
    export REDIRECT_OUT_ERR=
    function PREP_STEP() {
        :
    }
    function POST_STEP() {
        :
    }
export -f PREP_STEP
export -f POST_STEP

#
#-----------------------------------------------------------------------
#
# Add a postamble function
#
#-----------------------------------------------------------------------
#
function job_postamble() {

    # Print exit message
    print_info_msg "
========================================================================
Exiting script:  \"${scrfunc_fn}\"
In directory:    \"${scrfunc_dir}\"
========================================================================"
}

