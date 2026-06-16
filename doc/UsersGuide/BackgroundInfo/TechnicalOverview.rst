.. _TechOverview:

====================
Technical Overview
====================

This chapter provides information on prerequistes for running the workflow, and an overview of the workflow directory structure.

.. _Prerequisites:

Prerequisites for Using the verification workflow
===============================================

Background Knowledge Prerequisites
--------------------------------------

The instructions in this documentation assume that users have certain background knowledge: 

* Familiarity with LINUX/UNIX systems
* Command line basics
* System configuration knowledge (e.g., compilers, environment variables, paths, etc.)
* Numerical Weather Prediction (e.g., concepts of parameterizations: physical, microphysical, convective)
* Meteorology (in particular, meteorology at the scales being predicted: 25-km, 13-km, and 3-km resolutions)
* Verification concepts (skill scores, observation types, MET and METplus basics)

Additional background knowledge in the following areas could be helpful:

* High-Performance Computing (HPC) Systems (for those running the workflow on an HPC system)
* Programming (particularly Python and bash scripting) for those interested in contributing to the workflow code
* Creating an SSH Tunnel to access HPC systems from the command line
* Rocoto workflow manager

.. _software-prereqs:

Software/Operating System Requirements
-----------------------------------------
This workflow has been designed so that any sufficiently up-to-date machine with a UNIX-based operating system (Linux, MacOS) should be capable of running the application. SRW App :srw-wiki:`Level 1 systems <Supported-Platforms-and-Compilers>` already have these prerequisites installed. However, users working on other systems must ensure that the following requirements are installed on their system:

**Minimum Platform Requirements: NEED TO BE UPDATED**

* POSIX-compliant UNIX-style operating system

* If MET and/or METplus are not already installed on your machine, the prerequisite software needed for the latest `MET <https://metplus.readthedocs.io/projects/met/en/latest/Users_Guide/installation.html#required-external-libraries>`_ and <METplus <https://metplus.readthedocs.io/en/latest/Users_Guide/installation.html#requirements>`_ versions; as of this writing, this includes:

   * Python 3.12.0 or higher (Python 3.8.6+ may work, but some options may fail)
   * BUFRLIB (for reading PrepBufr Observation files)
   * netCDF4 (for reading and writing netCDF files)
   * HDF5 (for netCDF4 capabilities)

* git v2.12+ (for making/contributing code changes)

* Python package manager (conda or mamba recommended)

* wget (for retrieving observations and other data)

The following software is also required to run MET, but :term:`spack-stack` (which contains the software libraries necessary for building and running the SRW App) can be configured to build these requirements:

* CMake v3.20+

* :term:`MPI` (MPICH, OpenMPI, or other implementation)

* BUFRLIB, netCDF4, and HDF5

Optional but recommended prerequisites for all systems:

* Bash v4+
* Rocoto Workflow Management System (1.3.7+)


.. _Structure:

Code Repositories and Directory Structure
=========================================

.. _TopLevelDirStructure:

Repository Structure
----------------------
The |topdir| structure follows the standards laid out in the :term:`NCEP` Central Operations (NCO) WCOSS :nco:`Implementation Standards <ImplementationStandards.v11.0.0.pdf>`. Some files and directories have been removed for brevity.

.. code-block:: console

   dtc-vx-workflow
   ├── data_environment.yml
   ├── doc/
   │   └── UsersGuide/
   ├── environment.yml
   ├── jobs/
   │   ├── <TASKNAME>.sh
   ├── parm/
   │   ├── data_locations.yml
   │   ├── metplus/
   │   │   ├── <taskname>.conf
   │   │   ├── AZCA.poly
   │   │   ├── common.conf
   │   │   ├── EAST_OF_ROCKIES.poly
   │   │   ├── metplus_macros.jinja
   │   │   ├── plot_met_poly_points.py
   │   │   └── vx_configs/
   │   │       ├── vx_config_det.obs_gdas.model_aiml.yaml
   │   │       ├── vx_config_det.obs_gdas.model_gfs.yaml
   │   │       ├── vx_config_det.yaml
   │   │       └── vx_config_ens.yaml
   │   └── wflow/
   │       ├── default_workflow.yaml
   │       ├── verify_det.yaml
   │       ├── verify_ens.yaml
   │       └── verify_pre.yaml
   ├── README.md
   ├── scripts/
   │   ├── ascii2nc_obs.sh*
   │   ├── check_post_output.sh*
   │   ├── genensprod_or_ensemblestat.sh*
   │   ├── get_verif_obs.sh*
   │   ├── gridstat_or_pointstat_ensmean.sh*
   │   ├── gridstat_or_pointstat_ensprob.sh*
   │   ├── gridstat_or_pointstat.py
   │   ├── integration_test.py*
   │   ├── pb2nc_obs.sh*
   │   └── pcpcombine.sh*
   ├── setup_conda.sh
   ├── tests/
   │   ├── README.md
   │   ├── test_python/
   │   └── WE2E/
   │       ├── machine_suites/
   │       ├── monitor_jobs.py*
   │       ├── run_we2e_tests.py*
   │       ├── test_configs/
   │       │   └── verification/
   │       │       ├── config.<testname>.yaml
   │       ├── utils.py*
   │       ├── WE2E_summary.py*
   │       └── WE2E_tests.yaml
   └── ush/
       ├── bash_utils/
       ├── check_python_version.py*
       ├── cmp_rundirs_ncfiles.sh*
       ├── config_defaults.yaml
       ├── config_utils.py*
       ├── eval_metplus_timestr_tmpl.py
       ├── experiment.jsonschema
       ├── generate_wflow.py*
       ├── get_crontab_contents.py
       ├── get_metplus_tool_name.sh
       ├── get_obs.py
       ├── launch_vx_wflow.sh
       ├── load_modules_wflow.sh*
       ├── machine/
       ├── python_utils/
       ├── retrieve_data.py*
       ├── select_validtime_obs.py
       ├── set_cycle_and_obs_timeinfo.py
       ├── set_leadhrs.py
       ├── set_vx_params.py
       ├── set_vx_params.sh
       ├── setup.py
       ├── source_util_funcs.sh
       └── test_data/


Workflow Subdirectories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
:numref:`Table %s <Subdirectories>` describes the contents of the most important workflow subdirectories. :numref:`Table %s <FilesAndSubDirs>` provides a more comprehensive explanation of the |topdir| files and subdirectories. Users can reference the :nco:`NCO Implementation Standards <ImplementationStandards.v11.0.0.pdf>` (p. 19) for additional details on repository structure in NCO-compliant repositories. 

.. _Subdirectories:

.. list-table:: Subdirectories of the |topdir| repository
   :widths: 20 50
   :header-rows: 1

   * - Directory Name
     - Description
   * - conda
     - Installation location for miniconda and SRW App environments
   * - doc
     - Repository documentation
   * - exec
     - Executables built from code in ``/sorc``
   * - jobs
     - :term:`J-job <J-jobs>` scripts launched by Rocoto
   * - modulefiles
     - Files used to load modules needed for building and running the workflow
   * - parm
     - Parameter files used to configure the model, physics, workflow, and various SRW App components
   * - scripts
     - Scripts launched by the J-jobs
   * - sorc
     - External source code used to build the SRW App
   * - tests
     - Tests for baseline experiment configurations
   * - ush
     - Utility scripts used by the workflow
   
.. _ExperimentDirSection:

Experiment Directory Structure
--------------------------------
When the user generates an experiment using the ``generate_FV3LAM_wflow.py`` script (:numref:`Step %s <GenerateWorkflow>`), a user-defined experiment directory (``$EXPTDIR``) is created based on information specified in the ``config.yaml`` file. :numref:`Table %s <ExptDirStructure>` shows the contents of the experiment directory before running the experiment workflow.

.. _ExptDirStructure:

.. list-table:: *Files and subdirectories initially created in the experiment directory*
   :widths: 33 67
   :header-rows: 1

   * - File Name
     - Description
   * - config.yaml
     - Copy of the user-specified configuration file (see :numref:`Section %s <UserSpecificConfig>`)
   * - data_table
     - :term:`Cycle-independent` input file (empty)
   * - fd_ufs.yaml
     - The name of the field dictionary file. This file is a community-based dictionary for shared coupling fields and is automatically generated by the NUOPC Layer. 
   * - field_table
     - :term:`Tracers <tracer>` in the :ref:`forecast model field_table <ufs-wm:field_tableFile>`
   * - fix_am 
     - Directory containing the global fix (time-independent) data files (or symlinks to the fix files) for various fields on global grids (which are usually much coarser than the native FV3-LAM grid).
   * - fix_lam
     - Directory (initially empty) that will contain the regional fix (time-independent) data files (or symlinks to the fix files) that describe the regional grid, orography, and various surface climatology fields on the native FV3-LAM grid.
   * - FV3LAM_wflow.xml
     - Rocoto XML file to run the workflow
   * - input.nml
     - :term:`Namelist` for the :ref:`UFS Weather Model <ufs-wm:InputNML>`
   * - launch_FV3LAM_wflow.sh
     - Symlink to the ``dtc-vx-workflow/ush/launch_FV3LAM_wflow.sh`` shell script, 
       which can be used to (re)launch the Rocoto workflow. Each time this script is 
       called, it appends information to a log file named ``log.launch_FV3LAM_wflow``.
   * - log.generate_FV3LAM_wflow
     - Log of the output from the experiment generation script (``generate_FV3LAM_wflow.py``)
   * - rocoto_defns.yaml
     - YAML file containing the YAML workflow definition from which the Rocoto XML file is created.
   * - suite_{CCPP}.xml
     - :term:`CCPP` suite definition file (:term:`SDF`) used by the forecast model
   * - var_defns.yaml
     - YAML file containing the experiment parameters. It contains all of the primary 
       parameters specified in the default and user-specified configuration files plus 
       many secondary parameters that are derived from the primary ones by the 
       experiment generation script based on the machine files and other settings. 
       This file is the primary source of information on experiment variables used in the scripts at run time.
   * - task_skip_coldstart_YYYYMMDDHHmm.txt
     - Flag file for cold start 



Once the workflow is launched, several files and directories are generated. A log file named ``log.launch_FV3LAM_wflow`` will be created (unless it already exists) in ``$EXPTDIR``. The first several workflow tasks (i.e., ``make_grid``, ``make_orog``, ``make_sfc_climo``, ``get_extrn_ics``, and ``get_extrn_lbcs``) are preprocessing tasks, and these tasks also result in the creation of new files and subdirectories, described in :numref:`Table %s <CreatedByWorkflow>`.

.. _CreatedByWorkflow:

.. list-table:: *New directories and files created when the workflow is launched*
   :widths: 30 70
   :header-rows: 1

   * - Directory/File Name
     - Description
   * - YYYYMMDDHH
     - This is a “cycle directory” that is updated when the first cycle-specific 
       workflow tasks (``get_extrn_ics`` and ``get_extrn_lbcs``) are run. These tasks 
       are launched simultaneously for each cycle in the experiment. Cycle directories 
       are created to contain cycle-specific files for each cycle that the experiment 
       runs. If ``DATE_FIRST_CYCL`` and ``DATE_LAST_CYCL`` are different in the 
       ``config.yaml`` file, more than one cycle directory will be created under the 
       experiment directory.
   * - FV3LAM_wflow.db
       
       FV3LAM_wflow_lock.db
     - Database files that are generated when Rocoto is called (by the launch script) to launch the workflow
   * - grid
     - Directory generated by the ``make_grid`` task to store grid files for the experiment
   * - log
     - Directory containing log files generated by the overall workflow and by its various tasks. View the files in this directory to determine why a task may have failed.
   * - orog
     - Directory generated by the ``make_orog`` task containing the orography files for the experiment
   * - sfc_climo
     - Directory generated by the ``make_sfc_climo`` task containing the surface climatology files for the experiment
   
   
The output files for an experiment are described in :numref:`Section %s <OutputFiles>`.
The workflow tasks are described in :numref:`Section %s <WorkflowTaskDescription>`.
