# Add ush/ directory to PYTHONPATH so python script can access helper functions
if [ -n "${PYTHONPATH-}" ]; then
  export PYTHONPATH="$PYTHONPATH:$USHdir"
else
  export PYTHONPATH="$USHdir"
fi

# Set variable used for passing "--verbose" flag to python script
VERBOSE_FLAG=""
if [ "${VERBOSE}" = "True" ]; then
  VERBOSE_FLAG="--verbose"
fi

# For tasks that need an accumulation period, set ACCUM_ARG
ACCUM_ARG=""
if [ ! -z "${ACCUM_HH}" ]; then
  ACCUM_ARG="--accum_hh=${ACCUM_HH}"
fi

