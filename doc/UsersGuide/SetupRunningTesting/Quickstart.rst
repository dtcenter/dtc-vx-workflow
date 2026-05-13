.. _Quickstart:

====================
Quick Start Guide
====================

This chapter provides a brief summary of how to build and run the verification workflow.

**NOTE: The steps should run smoothly on** :srw-wiki:`Tier-1 <Supported-Platforms-and-Compilers>` **supported systems. Instructions for other platforms will be coming in the future.**


Install the Prerequisite Software Stack
=========================================
On Tier-1 supported systems such as Derecho and Hera, all prerequisites have already been installed.


Download data for tutorial case
===============================

For this tutorial case, we will download some RRFS prototype output to run verification tasks with. This tutorial will run on forecast hours 0 through 6:

  .. code-block:: console

     mkdir path/to/forecast/datadir
     cd path/to/datadir
     for i in $(seq 1 6); do
     wget https://noaa-ufs-srw-pds.s3.amazonaws.com/develop-20250321/output_data/fcst_det/RRFS_CONUS_25km/2019061500/postprd/rrfs.t00z.prslev.f00${i}.rrfs_conus_25km.grib2
     done

When finished, you should see seven grib files in your data directory:

  .. code-block:: console

     $ ls -al
     total 273064
     drwxr-sr-x 2 Michael.Kavulich gsd-fv3-dev     4096 Jan  8 21:03 .
     drwxr-sr-x 5 Michael.Kavulich gsd-fv3-dev     4096 Jan  8 20:59 ..
     -rw-r--r-- 1 Michael.Kavulich gsd-fv3-dev 20553322 Mar 22  2025 rrfs.t00z.prslev.f000.rrfs_conus_25km.grib2
     -rw-r--r-- 1 Michael.Kavulich gsd-fv3-dev 20199677 Mar 22  2025 rrfs.t00z.prslev.f001.rrfs_conus_25km.grib2
     -rw-r--r-- 1 Michael.Kavulich gsd-fv3-dev 20049464 Mar 22  2025 rrfs.t00z.prslev.f002.rrfs_conus_25km.grib2
     -rw-r--r-- 1 Michael.Kavulich gsd-fv3-dev 20009343 Mar 22  2025 rrfs.t00z.prslev.f003.rrfs_conus_25km.grib2
     -rw-r--r-- 1 Michael.Kavulich gsd-fv3-dev 19813959 Mar 22  2025 rrfs.t00z.prslev.f004.rrfs_conus_25km.grib2
     -rw-r--r-- 1 Michael.Kavulich gsd-fv3-dev 19643685 Mar 22  2025 rrfs.t00z.prslev.f005.rrfs_conus_25km.grib2
     -rw-r--r-- 1 Michael.Kavulich gsd-fv3-dev 19521654 Mar 22  2025 rrfs.t00z.prslev.f006.rrfs_conus_25km.grib2



.. _QuickSetup:

Setting up the verification workflow
===============================================

   #. Clone the workflow from GitHub:

      .. include:: ../../doc-snippets/clone.rst

   #. Load the Rocoto module. Rocoto is the workflow manager used to run verification experiments, and on most machines should be available by default:

      .. code-block:: console

         module load rocoto

      On Derecho, users will need to specify the location of the Rocoto modulefile:

      .. code-block:: console

         module use /glade/work/epicufsrt/contrib/derecho/modulefiles
         module load rocoto

      On Orion and Hercules, Rocoto is loaded from the "contrib" module

      .. code-block:: console

         module load contrib rocoto


   #. Load the python environment for the workflow. Sourcing this script will attempt to download and install a new ``conda`` installation in a subdirectory; users who wish to use an existing conda installation should build the environment found in ``environment.yml``

      .. include:: ../../doc-snippets/load-env.rst
      
      After sourcing this bash script, the appropriate environment should be loaded, and the user should see ``(vx_workflow)`` on their terminal prompt.

   #. Configure the experiment: 

      Copy the contents of the sample experiment from ``config.community.yaml`` to ``config.yaml``:

      .. code-block:: console

         cd ush
         cp config_tutorial.yaml config.yaml
      
      Users will need to open the ``config.yaml`` file and adjust the experiment parameters in it to suit the needs of their experiment (e.g., date, grid, physics suite). At a minimum, users need to modify the ``MACHINE`` parameter. In most cases, users will need to specify the ``ACCOUNT`` parameter and the location of the experiment data ``VX_FCST_INPUT_BASEDIR``.

      For example, a user on Hercules (login node 1) might adjust or add the following fields to run the 12-hr "out-of-the-box" case on Hercules using prestaged system data and :term:`cron` to automate the workflow: 

      .. code-block:: console
         
         user:
           MACHINE: hera
           ACCOUNT: epic
         workflow:
           DATE_FIRST_CYCL: '2019061500'
           DATE_LAST_CYCL: '2019061500'
           FCST_LEN_HRS: 6
           PREEXISTING_DIR_METHOD: rename
           taskgroups:
           - parm/wflow/verify_pre.yaml
           - parm/wflow/verify_det.yaml
           EXPT_SUBDIR: tutorial_case
         verification:
           VX_MASK:
           - CONUS
           - EAST
           - EAST_OF_ROCKIES
           VX_FCST_MODEL_NAME: 'rrfs'
           VX_FCST_INPUT_BASEDIR: /scratch4/BMC/gsd-fv3-dev/Michael.Kavulich/VX_workflow/quickstart_test/data
           FCST_FN_TEMPLATE: rrfs.t{init?fmt=%H?shift=-${time_lag}}z.prslev.f{lead?fmt=%HHH?shift=${time_lag}}.rrfs_conus_25km.grib2
           CCPA_OBS_DIR: '{{ workflow.EXPTDIR }}/obs_data/ccpa/proc'
           MRMS_OBS_DIR: '{{ workflow.EXPTDIR }}/obs_data/mrms/proc'
           NDAS_OBS_DIR: '{{ workflow.EXPTDIR }}/obs_data/ndas/proc'
           NOHRSC_OBS_DIR: '{{ workflow.EXPTDIR }}/obs_data/nohrsc/proc'
      
      Users on a different system would update the machine, account, and data paths accordingly.

Description of basic options
----------------------------

The verification workflow is highly configurable with a number of different options and tasks. This basic quick-start guide covers a simple deterministic verification using conventional observations. Additional examples can be found in :numref:`Section %s <Testing>` 

      **To be added: detailed descriptions of variables set in config_tutorial.yaml**

      All valid options can be found in the file ``ush/config_defaults.yaml``. More detailed guidance is available in :numref:`Section %s <UserSpecificConfig>` and :numref:`Section %s <ConfigWorkflow>`; particularly the variables in the ``verification:`` section described in :numref:`Section %s <VXParams>`.

   #. Generate the experiment workflow. 

      .. code-block:: console

         ./generate_FV3LAM_wflow.py

         ========================================================================
         Starting experiment generation...
         ========================================================================

         ========================================================================
         Starting function setup() in "setup.py"...
         ========================================================================

         ...
         ...
         ...

         ========================================================================

         Experiment generation completed.  The experiment directory is:

         EXPTDIR='/scratch4/BMC/gsd-fv3-dev/Michael.Kavulich/VX_workflow/quickstart_test/expt_dirs/tutorial_case'

         ========================================================================


   #. The workflow generation script helpfully provides instructions on how to run the workflow using Rocoto, including instructions on how to automate from a crontab.

      .. code-block:: console
         
         cd $EXPTDIR
         rocotorun -w vx_wflow.xml -d vx_wflow.db -v 10
         rocotostat -w FV3LAM_wflow.xml -d FV3LAM_wflow.db -v 10

   **Instructions on automatic submission and monitoring of jobs will be coming**   

