# DO NOT RUN THIS SCRIPT AS A SHELL SCRIPT: IT MUST BE INVOKED USING THE source BUILTIN
(return 0 2>/dev/null) || {
    echo "ERROR: This script must be sourced, not executed." >&2
    exit 1
}

# Resolve the directory containing this script so that all relative paths
# (conda_loc, conda/, environment.yml) work regardless of the caller's CWD.
SCRIPT_DIR=$(builtin cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# If the conda location file does not exist but a conda installation exists under
# dtc-vx-workflow/ from a previous installation, check if user wants to use it.
# This is a legacy check for environments created with an older version of this script
if [ ! -f "${SCRIPT_DIR}/conda_loc" ] && [ -d "${SCRIPT_DIR}/conda" ] ; then
  echo "Found existing conda installation in conda/ subdirectory"
  read -p "Do you want to use the existing conda build? (y/n) " -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]] ; then
    EXISTING_CONDA_BUILD="$(builtin cd "${SCRIPT_DIR}/conda" && pwd)"
    echo "${EXISTING_CONDA_BUILD}" > "${SCRIPT_DIR}/conda_loc"
    echo "Created conda_loc pointing to: ${EXISTING_CONDA_BUILD}"
  fi
fi

# Check if user has an existing system-level conda install
USE_SYSTEM_CONDA=false
if [ ! -f "${SCRIPT_DIR}/conda_loc" ] && command -v conda &> /dev/null ; then
  CONDA_BASE=$(conda info --base)
  echo "Found existing conda installation at: ${CONDA_BASE}"
  read -p "Do you want to use your existing system conda? (y/n) " -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]] ; then
    USE_SYSTEM_CONDA=true
    echo "Using system conda installation..."
    # Initialize conda if not already initialized
    . "${CONDA_BASE}/etc/profile.d/conda.sh" 2>/dev/null || true
    echo "${CONDA_BASE}" > "${SCRIPT_DIR}/conda_loc"
  else
    echo "Proceeding with local conda installation..."
  fi
else
  echo "No existing conda installation detected"
fi

if [ "$USE_SYSTEM_CONDA" = false ] ; then
  if [ -f "${SCRIPT_DIR}/conda_loc" ] ; then
    CONDA_BUILD_DIR=$(cat "${SCRIPT_DIR}/conda_loc")
    echo "Using conda from conda_loc: ${CONDA_BUILD_DIR}"
  else
    CONDA_BUILD_DIR="${SCRIPT_DIR}/conda"
    echo "Building local conda install in ${CONDA_BUILD_DIR}/"
  fi
  os=$(uname)
  if [ ! -d "${CONDA_BUILD_DIR}" ] ; then
    test $os == Darwin && os=MacOSX
    hardware=$(uname -m)
    installer=Miniforge3-${os}-${hardware}.sh
    curl -L -O "https://github.com/conda-forge/miniforge/releases/download/23.3.1-1/${installer}"
    bash ./${installer} -bfp "${CONDA_BUILD_DIR}"
    rm -f ${installer}
  fi

  . ${CONDA_BUILD_DIR}/etc/profile.d/conda.sh
  # Put some additional packages in the base environment on MacOS systems
  if [ "${os}" == "MacOSX" ] ; then
    mamba install -y bash coreutils sed
  fi

  CONDA_BUILD_DIR="$(builtin cd "${CONDA_BUILD_DIR}" && pwd)"
  if [ -z "${CONDA_BUILD_DIR}" ] ; then
    echo "ERROR: Could not resolve conda installation path." >&2
    return 1
  fi
  if [ ! -f "${SCRIPT_DIR}/conda_loc" ] ; then
    echo "${CONDA_BUILD_DIR}" > "${SCRIPT_DIR}/conda_loc"
  fi
  echo "Local conda build location: ${CONDA_BUILD_DIR}"

  if [[ ! "$PATH" =~ "$CONDA_BUILD_DIR" ]]; then
    export PATH=${CONDA_BUILD_DIR}/condabin:${CONDA_BUILD_DIR}/bin:${PATH}
  fi
  if [[ -z "${LD_LIBRARY_PATH:-}" ]]; then
    export LD_LIBRARY_PATH=${CONDA_BUILD_DIR}/lib
  elif [[ ! "${LD_LIBRARY_PATH}" =~ "$CONDA_BUILD_DIR" ]]; then
    export LD_LIBRARY_PATH=${CONDA_BUILD_DIR}/lib:${LD_LIBRARY_PATH}
  fi
fi

conda activate

# Select which conda environment to create/load based on the (optional) first argument:
#   (none)   -> vx_workflow (main workflow environment)
#   vx_diff  -> vx_diff      (regression-test diff utility)
#   vcast    -> vcast        (VCasT plotting/statistics tool)
ENV_NAME=$1
if [ "${ENV_NAME}" == vx_diff ]; then
  ENV_YAML=${SCRIPT_DIR}/tests/regression/environment.yml
elif [ "${ENV_NAME}" == vcast ]; then
  ENV_YAML=${SCRIPT_DIR}/vcast_environment.yml
else
  ENV_NAME=vx_workflow
  ENV_YAML=${SCRIPT_DIR}/environment.yml
fi

if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME}\s" ; then
  echo "Creating ${ENV_NAME} environment..."
  mamba env create -n ${ENV_NAME} --file "${ENV_YAML}" --quiet
else
  read -p "${ENV_NAME} environment has already been built. Check for updates using environment.yml? (y/n) " -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]] ; then
    echo "Updating ${ENV_NAME} environment..."
    mamba env update -n ${ENV_NAME} --file "${ENV_YAML}" --prune --quiet
  fi
fi

conda activate ${ENV_NAME}
