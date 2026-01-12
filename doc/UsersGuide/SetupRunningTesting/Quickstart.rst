.. _Quickstart:

====================
Quick Start Guide
====================

This chapter provides a brief summary of how to build and run the verification workflow. The steps will run most smoothly on :srw-wiki:`SRW Level 1 <Supported-Platforms-and-Compilers>` systems. Users should expect to reference other chapters of this User's Guide, particularly :numref:`Section %s: Setting up the workflow <Setup>` and :numref:`Section %s: Running the workflow <RunVX>`, for additional explanations regarding each step.


Install the Prerequisite Software Stack
=========================================
The main prerequisites that are needed for running the workflow are MET and METplus. Users who are **not** working on an :srw-wiki:`SRW Level 1 <Supported-Platforms-and-Compilers>` platform will need to install the prerequisite software stack on their own; this can be done via :term:`spack-stack` or by installing MET and METplus according to their respective installation guides. Users wishing to use spack-stack can find installation instructions in the :doc:`spack-stack documentation <spack-stack:index>`. The steps will vary slightly depending on the user's platform, but detailed instructions for a variety of platforms are available in the documentation. Users may also post questions in the `workflow repository Discussions tab <https://github.com/dtcenter/dtc-vx-workflow/discussions/>`__.

Once prerequisites have been successfully installed, users can move on to setting up the workflow.


Download data for tutorial case
===============================

If you are on an :srw-wiki:`SRW Level 1 <Supported-Platforms-and-Compilers>`, you can skip this section as the tutorial data should already be available on disk.



.. _QuickSetup:

Setting up the verification workflow
===============================================

For a detailed explanation of how to set up the workflow on any supported system, see :numref:`Section %s: Setting up the workflow <Setup>` and :numref:`Section %s: Running the workflow <RunVX>`. The overall procedure for generating an experiment is shown in :numref:`Figure %s <OverallProc>`, with the scripts to generate and run the workflow shown in red. An overview of the required steps appears below. However, users can expect to access other referenced sections of this User's Guide for more detail.

   #. Clone the workflow from GitHub:

      .. include:: ../../doc-snippets/clone.rst

   #. Users on a :srw-wiki:`SRW Level 2-4 <Supported-Platforms-and-Compilers>` system must download and stage data (both the fix files and the :term:`IC/LBC <ICs/LBCs>` files) according to the instructions in :numref:`Section %s <DownloadingStagingInput>`. Standard data locations for SRW Level 1 systems appear in :numref:`Table %s <DataLocations>`.

   #. Load the python environment for the workflow. Sourcing this script will attempt to download and install a new ``conda`` installation in a subdirectory; users who wish to use an existing conda installation should build the environment found in ``environment.yml``

      .. include:: ../../doc-snippets/load-env.rst
      
      After sourcing this bash script, the appropriate environment should be loaded, and the user should see ``(vx_workflow)`` on their terminal prompt.

   #. Configure the experiment: 

      Copy the contents of the sample experiment from ``config.community.yaml`` to ``config.yaml``:

      .. code-block:: console

         cd ush
         cp config.community.yaml config.yaml
      
      Users will need to open the ``config.yaml`` file and adjust the experiment parameters in it to suit the needs of their experiment (e.g., date, grid, physics suite). At a minimum, users need to modify the ``MACHINE`` parameter. In most cases, users will need to specify the ``ACCOUNT`` parameter and the location of the experiment data (see :numref:`Section %s <Data>` for Level 1 system default locations). 

      For example, a user on Hercules (login node 1) might adjust or add the following fields to run the 12-hr "out-of-the-box" case on Hercules using prestaged system data and :term:`cron` to automate the workflow: 

      .. code-block:: console
         
         user:
           MACHINE: hercules
           ACCOUNT: epic
         workflow:
           EXPT_SUBDIR: run_basic_srw
           USE_CRON_TO_RELAUNCH: true
           CRON_RELAUNCH_INTVL_MNTS: 3
         task_get_extrn_ics:
           USE_USER_STAGED_EXTRN_FILES: true
           EXTRN_MDL_SOURCE_BASEDIR_ICS: /work/noaa/epic/role-epic/contrib/UFS_SRW_data/develop/input_model_data/FV3GFS/grib2/${yyyymmddhh}
         task_get_extrn_lbcs:
           USE_USER_STAGED_EXTRN_FILES: true
           EXTRN_MDL_SOURCE_BASEDIR_LBCS: /work/noaa/epic/role-epic/contrib/UFS_SRW_data/develop/input_model_data/FV3GFS/grib2/${yyyymmddhh}
      
      Users on a different system would update the machine, account, and data paths accordingly. Additional changes may be required based on the system and experiment. More detailed guidance is available in :numref:`Section %s <UserSpecificConfig>`. Parameters and valid values are listed in :numref:`Section %s <ConfigWorkflow>`. 

   #. Generate the experiment workflow. 

      .. code-block:: console

         ./generate_FV3LAM_wflow.py

   #. Run the workflow from the experiment directory (``$EXPTDIR``). By default, the path to this directory is ``${EXPT_BASEDIR}/${EXPT_SUBDIR}`` (see :numref:`Section %s <DirParams>` for more detail). There are several methods for running the workflow, which are discussed in :numref:`Section %s <Run>`. Most require the :ref:`Rocoto Workflow Manager <RocotoInfo>`. For example, if the user automated the workflow using cron, run: 

      .. code-block:: console
         
         cd $EXPTDIR
         rocotostat -w FV3LAM_wflow.xml -d FV3LAM_wflow.db -v 10
   
      The user can resubmit the ``rocotostat`` command as needed to check the workflow progress.

      If the user has Rocoto but did *not* automate the workflow using :term:`cron`, run: 

      .. code-block:: console

         cd $EXPTDIR
         ./launch_FV3LAM_wflow.sh

      To (re)launch the workflow and check the experiment's progress, run:

      .. code-block:: console

         ./launch_FV3LAM_wflow.sh; tail -n 40 log.launch_FV3LAM_wflow

      The workflow must be relaunched regularly and repeatedly until the log output includes a ``Workflow status: SUCCESS`` message indicating that the experiment has finished.

Optionally, users may :ref:`configure their own grid <UserDefinedGrid>` or :ref:`vertical levels <VerticalLevels>` instead of using a predefined grid and default set of vertical levels. Users can also :ref:`plot the output <PlotOutput>` of their experiment(s) or :ref:`run verification tasks using METplus <vxconfig>`.
