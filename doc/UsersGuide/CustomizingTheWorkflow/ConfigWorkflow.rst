.. _ConfigWorkflow:

================================================================================================
Workflow Parameters: Configuring the Workflow in ``config.yaml`` and ``config_defaults.yaml``		
================================================================================================
To create an experiment with the verification workflow, the user must create an experiment configuration file (named ``config.yaml`` by default). This file contains experiment-specific information, such as dates, paths to data and utilities, forecast and observation settings, and other relevant settings. 

There is an extensive list of experiment parameters that a user can set when configuring the experiment. Not all of these parameters need to be set explicitly by the user in ``config.yaml``. If a user does not define a variable in the ``config.yaml`` script, its value in ``config_defaults.yaml`` will be used, or the value will be reset depending on other parameters, such as the platform (``MACHINE``) selected for the experiment. 

The configuration file supports many custom functions for defining variables through ``uwtools``. For example, referencing the value of other variables can be done within a string by prefixing the variable of interest with the section (and possibly subsection) it is found in, and wrapping that definition in double curly brackets. For example:

.. code-block:: console

   workflow:
     EXPTDIR: '/path/to/experiment'
   verification:
     VX_FCST_INPUT_BASEDIR: '{{ workflow.EXPTDIR }}' # Filled in as string '/path/to/experiment'

Mathematical and Jinja logical experssions are also supported:

.. code-block:: console

   ensemble:
     NUM_ENS_MEMBERS: 3
     ENSMEM_NAMES: '{% for m in range(ensemble.NUM_ENS_MEMBERS) %}{{ "mem%03d, " % m }}{% endfor %}' # Filled in as 'mem001, mem002, mem003'
   regriddataplane:
     execution:
       tasks_per_node: '{{ regriddataplane.TASKS }}' # Filled in as string '1'
       walltime: 00:30:00
       memory: '{{ 10 * regriddataplane.TASKS }}G' # Filled in as string '10G'
     TASKS: 1

Note that, in order for these templates to be filled in by ``uwtools``, the templates must be contained in strings. If a non-string value must be specified, the ``uwtools`` YAML language supports several pyYAML tags that apply appropriate typing. You can find more information about the Custom Tags in the `uwtools docs <https://uwtools.readthedocs.io/en/main/sections/user_guide/yaml/tags.html>`__. For example, those may be ``!int``, ``!float``, ``!bool``, etc.

.. code-block:: console

   workflow:
     FCST_LEN_HRS: 24
     FCST_LEN_CYCL:
       - !int '{{ workflow.FCST_LEN_HRS }}' # Results in a single-element list [ 24 ]
     LONG_FCST_LEN: !int '{{ workflow.FCST_LEN_CYCL|max if workflow.FCST_LEN_HRS < 0 else workflow.FCST_LEN_HRS }}' # Results in the integer 24


.. _METParamNote:

.. note::
   Where a date field is required:
      * ``YYYY`` refers to the 4-digit valid year
      * ``MM`` refers to the 2-digit valid month
      * ``DD`` refers to the 2-digit valid day of the month
      * ``HH`` refers to the 2-digit valid hour of the day
      * ``mm`` refers to the 2-digit valid minutes of the hour
      * ``SS`` refers to the two-digit valid seconds of the hour

.. _user:

``user:``
======================================

This section describes the valid ``user:`` config settings.

``MACHINE``: (Default: "BIG_COMPUTER")
   The machine (a.k.a. platform or system) on which the workflow will run. Currently supported platforms can be found by referencing the platform definition files found in ``ush/machine/``. 

``ACCOUNT``: (Default: "")
   The account under which users submit jobs to the queue on the specified ``MACHINE``. This is required in order to charge the correct account for the submitted jobs on an HPC system. On most HPC systems, you can determine which projects you have access to with the ``account_params`` or ``saccount_params`` command.

Workflow Directories
--------------------------

``HOMEdir``: (Default: ``'{{ user.HOMEdir }}'``)
   The path to the user's ``dtc-vx-workflow`` clone. This path is set in ``ush/setup.py`` as the parent directory to ``USHdir``. 

``USHdir``: (Default: ``'{{ user.USHdir }}'``)
   The path to the user's ``ush`` directory in their ``dtc-vx-workflow`` clone. This path is set automatically in the main function of ``setup.py`` and corresponds to the location of ``setup.py`` (i.e., the ``ush`` directory).

``SCRIPTSdir``: (Default: ``'{{ user.HOMEdir }}/scripts'``)
   The path to the user's ``scripts`` directory in their ``dtc-vx-workflow`` clone.

``JOBSdir``: (Default: ``'{{ user.HOMEdir }}/jobs'``)
   The path to the user's ``jobs`` directory in their ``dtc-vx-workflow`` clone.

``PARMdir``: (Default: ``'{{ user.HOMEdir }}/parm'``)
   The path to the user's ``parm`` directory in their ``dtc-vx-workflow`` clone.

``METPLUS_CONF``: (Default: ``'{{ user.PARMdir }}/metplus'``)
   The path to the directory where the user's final METplus configuration file resides. By default, METplus configuration files reside in ``dtc-vx-workflow/parm/metplus``. 

.. _PlatformConfig:

.. _user:

``platform:``
======================================

This section describes the valid ``platform:`` config settings. 

``WORKFLOW_MANAGER``: (Default: "none")
   The workflow manager to use (e.g., "rocoto"). This is set to "none" by default, but if the machine name is set to a platform that supports Rocoto, this will be overwritten and set to "rocoto." If set explicitly to "rocoto" along with the use of the ``MACHINE: "LINUX"`` target, the configuration layer assumes a Slurm batch manager when generating the XML. Valid values: ``"rocoto"`` | ``"none"``

   .. note:: 

      The ability to generate an ``ecflow`` workflow is not yet available in the SRW App. Although ``ecflow`` has been added to ``ush/valid_param_vals.yaml`` as a valid option, setting this option will fail to produce a functioning workflow. 
      Without the necessary ``ecf`` directory, it is impossible to generate ``ecflow`` workflows at this time. The addition of this functionality is planned but not yet completed. 

``NCORES_PER_NODE``: (Default: "")
   The number of cores available per node on the compute platform. Set for supported platforms in ``setup.py``, but it is now also configurable for all platforms.

``TASKTHROTTLE``: (Default: 1000)
  The number of active tasks that can be run simultaneously via Rocoto. For Linux/MacOS systems, it makes sense to set this to 1 because these systems often have a small number of available cores/CPUs and therefore less capacity to run multiple tasks simultaneously. 
``CYCLETHROTTLE``: (Default: 200)
  The number of active forecast cycles that can be run simultaneously via Rocoto.

.. _sched:

``SCHED``: (Default: "")
   The job scheduler to use (e.g., Slurm) on the specified ``MACHINE``. Leaving this an empty string allows the experiment generation script to set it automatically depending on the machine the workflow is running on. Valid values: ``"slurm"`` | ``"pbspro"`` | ``"lsf"`` | ``"lsfcray"`` | ``"none"``


Machine-Dependent Parameters
-------------------------------
These parameters vary depending on machine. On :srw-wiki:`Level 1 and 2 <Supported-Platforms-and-Compilers>` systems, the appropriate values for each machine can be viewed in the ``ush/machine/<platform>.sh`` scripts. To specify a value other than the default, add these variables and the desired value in the ``config.yaml`` file so that they override the ``config_defaults.yaml`` and machine default values. 

``PARTITION_DEFAULT``: (Default: "")
   This variable is only used with the Slurm job scheduler (i.e., when ``SCHED: "slurm"``). This is the default partition to which Slurm submits workflow tasks. Unless a task makes use of an alternative partition such as ``PARTITION_HPSS`` (see below), the task will be submitted to the default partition indicated in the ``PARTITION_DEFAULT`` variable. If this value is not set or is set to an empty string, it will be (re)set to a machine-dependent value. Options are machine-dependent and include: ``""`` | ``"hera"`` | ``"normal"`` | ``"orion"`` | ``"sjet"`` | ``"vjet"`` | ``"kjet"`` | ``"xjet"`` | ``"workq"``

``QUEUE_DEFAULT``: (Default: "")
   The default queue or QOS to which workflow tasks are submitted (QOS is Slurm's term for queue; it stands for "Quality of Service"). Unless a task makes use of an alternative queue such as ``QUEUE_HPSS`` (see below), the task will be submitted to the queue indicated by this variable. If this value is not set or is set to an empty string, it will be (re)set to a machine-dependent value. Options are machine-dependent and include: ``""`` | ``"batch"`` | ``"dev"`` | ``"normal"`` | ``"regular"`` | ``"workq"``

``PARTITION_HPSS``: (Default: "")
   This variable is only used with the Slurm job scheduler (i.e., when ``SCHED: "slurm"``). Tasks that get or create links to external model files are submitted to the partition specified in this variable. These links are needed to generate initial conditions (:term:`ICs`) and lateral boundary conditions (:term:`LBCs`) for the experiment. If this variable is not set or is set to an empty string, it will be (re)set to the ``PARTITION_DEFAULT`` value (if set) or to a machine-dependent value. Options are machine-dependent and include: ``""`` | ``"normal"`` | ``"service"`` | ``"workq"``

``QUEUE_HPSS``: (Default: "")
   Tasks that get or create links to external model files are submitted to this queue, or QOS (QOS is Slurm's term for queue; it stands for "Quality of Service"). These links are needed to generate initial conditions (:term:`ICs`) and lateral boundary conditions (:term:`LBCs`) for the experiment. If this value is not set or is set to an empty string, it will be (re)set to a machine-dependent value. Options are machine-dependent and include: ``""`` | ``"batch"`` | ``"dev_transfer"`` | ``"normal"`` | ``"regular"`` | ``"workq"``

``REMOVE_MEMORY``: (Default: False)
  Boolean flag that determines whether to remove the memory flag for the Rocoto XML. Some platforms are not configured to accept the memory flag, so it must not be included in the XML. Valid values: ``True`` | ``False``

Parameters for Running Without a Workflow Manager
-----------------------------------------------------
These settings define platform-specific run commands. Users should set run commands for platforms without a workflow manager. These values will be ignored unless ``WORKFLOW_MANAGER: "none"``.

``RUN_CMD_PRDGEN``: (Default: "")
  The run command for the product generation job.

``RUN_CMD_SERIAL``: (Default: "")
  The run command for some serial jobs.

``SCHED_NATIVE_CMD``: (Default: "")
   Allows an extra parameter to be passed to the job scheduler (Slurm or PBSPRO) via XML Native command. 

``PRE_TASK_CMDS``: (Default: "")
   Pre-task commands such as ``ulimit`` needed by tasks. For example: ``'{ ulimit -s unlimited; ulimit -a; }'``

Paths for MET and METplus
-------------------------
``MET_INSTALL_DIR``: (Default: "")
  Directory where MET binary executables can be found. The workflow will look in the subdirectory ${MET_INSTALL_DIR}/bin for MET executables.

``METPLUS_ROOT``: (Default: "")
  Directory where METplus wrappers and other METplus files can be found. The workflow will look in the subdirectory ${METPLUS_ROOT}/metplus/wrappers/ for METplus wrappers, and ${METPLUS_ROOT}/share/met/poly/ for VX mask polygons.


Test Directories
----------------------

These directories are used only by the ``run_WE2E_tests.py`` script, so they are not used unless the user runs a Workflow End-to-End (WE2E) test (see :numref:`Section %s <WE2E_tests>`). Their function corresponds to the same variables without the ``TEST_`` prefix. Users typically should not modify these variables. For any alterations, the logic in the ``run_WE2E_tests.py`` script would need to be adjusted accordingly.

``TEST_EXTRN_MDL_SOURCE_BASEDIR``: (Default: "")
   This parameter allows testing of user-staged files in a known location on a given platform. This path contains a limited dataset and likely will not be useful for most user experiments. 

``TEST_ALT_EXTRN_MDL_SYSBASEDIR_ICS``, ``TEST_ALT_EXTRN_MDL_SYSBASEDIR_LBCS``: (Default: "")
   These parameters are used by the testing script to test the mechanism that allows users to point to a data stream on disk. They set up a sandbox location that mimics the stream in a more controlled way and test the ability to access :term:`ICS` or :term:`LBCS`, respectively. 

``TEST_CCPA_OBS_DIR``, ``TEST_MRMS_OBS_DIR``, ``TEST_NDAS_OBS_DIR``, ``TEST_NOHRSC_OBS_DIR``, ``TEST_AERONET_OBS_DIR``, ``TEST_AIRNOW_OBS_DIR``: (Default: "")
These parameters are used by the testing script to test the mechanism that allows user to point to data streams on disk for observation data for verification tasks. They test the ability for users to set ``CCPA_OBS_DIR``, ``MRMS_OBS_DIR``, ``NDAS_OBS_DIR``, etc.

``TEST_VX_FCST_INPUT_BASEDIR``: (Default: "") 
   The path to user-staged forecast files for WE2E testing of verificaton using user-staged forecast files in a known location on a given platform. 

``STAGED_DATA``: (Default: "")
   The base path to staged test data for WE2E testing.

.. _SystemFixedFiles:

Fixed File Directory Parameters
----------------------------------

These parameters are associated with the fixed (i.e., static) files. Because the default values are platform-dependent, they are set to a null string in ``config_defaults.yaml``.

``EXTRN_MDL_DATA_STORES``: (Default: "")
   A list of data stores where the scripts should look for external model data. The list is in priority order. If disk information is provided via ``USE_USER_STAGED_EXTRN_FILES`` or a known location on the platform, the disk location will be highest priority. Valid values (in priority order): ``disk`` | ``hpss`` | ``aws`` | ``nomads``. 

``BEST_TRACK``: (Default: "")
   Staged location on disk for TC "best track" data

.. _workflow:

``workflow:``
======================================

This section describes the valid ``workflow:`` config settings. 

``taskgroups``: (Default:

.. code-block:: console

     - parm/wflow/verify_pre.yaml
     - parm/wflow/verify_det.yaml

)
   Users are most likely to use the ``taskgroups:`` entry to add or delete groups of tasks from the default list of tasks. For example, to add ensemble verification tasks, users would set:

.. code-block:: console

   taskgroups: 
     - parm/wflow/verify_pre.yaml
     - parm/wflow/verify_det.yaml
     - parm/wflow/verify_ens.yaml

``WORKFLOW_ID``: (Default: "")
   Unique ID for the workflow run that will be set in ``setup.py``.

``RELATIVE_LINK_FLAG``: (Default: "--relative")
   How to make links. The default is relative links; users may set an empty string for absolute paths in links.

.. _Cron:

Cron-Associated Parameters
------------------------------

Cron is a job scheduler accessed through the command-line on UNIX-like operating systems. It is useful for automating tasks such as the ``rocotorun`` command, which launches each workflow task in the SRW App. Cron periodically checks a cron table (aka crontab) to see if any tasks are ready to execute. If so, it runs them. 

``USE_CRON_TO_RELAUNCH``: (Default: false)
   Flag that determines whether to add a line to the user's cron table, which calls the experiment launch script every ``CRON_RELAUNCH_INTVL_MNTS`` minutes. Valid values: ``True`` | ``False``

``CRON_RELAUNCH_INTVL_MNTS``: (Default: 3)
   The interval (in minutes) between successive calls of the experiment launch script by a cron job to (re)launch the experiment (so that the workflow for the experiment kicks off where it left off). This is used only if ``USE_CRON_TO_RELAUNCH`` is set to true.

``CRONTAB_LINE``: (Default: "")
   The launch command that will appear in the crontab (e.g., ``*/3 * * * * cd <path/to/experiment/subdirectory> && ./launch_FV3LAM_wflow.sh called_from_cron="TRUE"``).

.. _DirParams:

Directory Parameters
-----------------------

``EXPT_BASEDIR``: (Default: "")
   The full path to the base directory in which the experiment directory (``EXPT_SUBDIR``) will be created. If this is not specified or if it is set to an empty string, it will default to ``${HOMEdir}/../expt_dirs``, where ``${HOMEdir}`` contains the full path to the ``dtc-vx-workflow`` directory. If set to a relative path, the provided path will be appended to the default value ``${HOMEdir}/../expt_dirs``. For example, if ``EXPT_BASEDIR=some/relative/path`` (i.e. a path that does not begin with ``/``), the value of ``EXPT_BASEDIR`` used by the workflow will be ``EXPT_BASEDIR=${HOMEdir}/../expt_dirs/some/relative/path``.

``EXPT_SUBDIR``: (Default: 'experiment')
   If ``EXPTDIR`` is not specified, ``EXPT_SUBDIR`` represents the name of the experiment directory (*not* the full path). 

``EXPTDIR``: (Default: ``'{{ workflow.EXPT_BASEDIR }}/{{ workflow.EXPT_SUBDIR }}'``)
   The full path to the experiment directory. By default, this value will point to ``"${EXPT_BASEDIR}/${EXPT_SUBDIR}"``, but the user can define it differently in the configuration file if desired. 

``WFLOW_FLAG_FILES_DIR``: (Default: ``'{{ workflow.EXPTDIR }}/wflow_flag_files'``)
    Directory in which flag files marking completion of various workflow tasks can be placed.

*Experiment Directory* Files and Paths
------------------------------------------

This section contains files and paths to files that are staged in the experiment directory at configuration time. 

``WFLOW_XML_FN``: (Default: "FV3LAM_wflow.xml")
   Name of the Rocoto workflow XML file that the experiment generation script creates. This file defines the workflow for the experiment.

``GLOBAL_VAR_DEFNS_FN``: (Default: "var_defns.yaml")
   Name of the auto-generated experiment configuration file. It contains the primary experiment variables defined in this default configuration script and in the user-specified configuration as well as secondary experiment variables generated by the experiment generation script from machine files and other settings. This file is the primary source of information used in the scripts at run time.

``ROCOTO_YAML_FN``: (Default: "rocoto_defns.yaml")
   Name of the YAML file containing the YAML workflow definition from which the Rocoto XML file is created.

``EXTRN_MDL_VAR_DEFNS_FN``: (Default: "extrn_mdl_var_defns")
   Name of the file (a shell script) containing the definitions of variables associated with the external model from which :term:`ICs` or :term:`LBCs` are generated. This file is created by the ``GET_EXTRN_*`` task because the values of the variables it contains are not known before this task runs. The file is then sourced by the ``MAKE_ICS`` and ``MAKE_LBCS`` tasks.

``WFLOW_LAUNCH_SCRIPT_FN``: (Default: "launch_FV3LAM_wflow.sh")
   Name of the script that can be used to (re)launch the experiment's Rocoto workflow.

``WFLOW_LAUNCH_LOG_FN``: (Default: "log.launch_FV3LAM_wflow")
   Name of the log file that contains the output from successive calls to the workflow launch script (``WFLOW_LAUNCH_SCRIPT_FN``).

``GLOBAL_VAR_DEFNS_FP``: (Default: ``'{{ workflow.EXPTDIR }}/{{ workflow.GLOBAL_VAR_DEFNS_FN }}'``) 
   Path to the global variable definition file (``GLOBAL_VAR_DEFNS_FN``) in the experiment directory. 

``ROCOTO_YAML_FP``: (Default: ``'{{ workflow.EXPTDIR }}/{{ workflow.ROCOTO_YAML_FN }}'``)
   Path to the Rocoto YAML configuration file (``ROCOTO_YAML_FN``) in the experiment directory. 

``WFLOW_LAUNCH_SCRIPT_FP``: (Default: ``'{{ user.USHdir }}/{{ workflow.WFLOW_LAUNCH_SCRIPT_FN }}'``) 
   Path to the workflow launch script (``WFLOW_LAUNCH_SCRIPT_FN``) in the experiment directory. 

``WFLOW_LAUNCH_LOG_FP``: (Default: ``'{{ workflow.EXPTDIR }}/{{ workflow.WFLOW_LAUNCH_LOG_FN }}'``) 
   Path to the log file (``WFLOW_LAUNCH_LOG_FN``) in the experiment directory that contains output from successive calls to the workflow launch script. 


Forecast Parameters
----------------------
``DATE_FIRST_CYCL``: (Default: "YYYYMMDDHH")
   Starting cycle date of the first forecast in the set of forecasts to run. Format is "YYYYMMDDHH".

``DATE_LAST_CYCL``: (Default: "YYYYMMDDHH")
   Starting cycle date of the last forecast in the set of forecasts to run. Format is "YYYYMMDDHH".

``INCR_CYCL_FREQ``: (Default: 24)
   Increment in hours for Rocoto cycle frequency. The default is 24, which means cycl_freq=24:00:00.

``FCST_LEN_HRS``: (Default: 24)
   The length of each forecast in integer hours. (Or the short forecast length when there are different lengths.)

``LONG_FCST_LEN_HRS``: (Default: ``'{% if FCST_LEN_HRS < 0 %}{{ FCST_LEN_CYCL|max }}{% else %}{{ FCST_LEN_HRS }}{% endif %}'``)
   The length of the longer forecast in integer hours in a system that varies the length of the forecast by time of day. There is no need for the user to update this value directly, as it is derived from ``FCST_LEN_CYCL`` when ``FCST_LEN_HRS=-1``.

``FCST_LEN_CYCL``: (Default: ``- '{{ FCST_LEN_HRS }}'``)
   The length of forecast for each cycle in a given day (in integer hours). This is valid only when ``FCST_LEN_HRS = -1``. This pattern recurs for all cycle dates. Must have the same number of entries as cycles per day (as defined by 24/``INCR_CYCL_FREQ``), or if less than one day the entries must include the length of each cycle to be run. By default, it is set to a 1-item list containing the standard fcst length. 

.. hint::
   The interaction of ``FCST_LEN_HRS``, ``LONG_FCST_LEN_HRS``, and ``FCST_LEN_CYCL`` can be confusing. As an example, take an experiment with cycling every three hours, a short forecast length of 18 hours, and a long forecast length of 48 hours. The long forecasts are run at 0 and 12 UTC. Users would put the following entry in their configuration file: 

      .. code-block:: console

         FCST_LEN_HRS: -1
         FCST_LEN_CYCL: 
           - 48
           - 18
           - 18 
           - 18 
           - 48
           - 18
           - 18
           - 18

   By setting ``FCST_LEN_HRS: -1``, the experiment will derive the values of ``FCST_LEN_HRS`` (18) and ``LONG_FCST_LEN_HRS`` (48) for each cycle date. 

.. _preexisting-dirs:

Pre-Existing Directory Parameter
------------------------------------
``PREEXISTING_DIR_METHOD``: (Default: "quit")
   This variable determines how to deal with pre-existing directories (resulting from previous calls to the experiment generation script using the same experiment name [``EXPT_SUBDIR``] as the current experiment). This variable must be set to one of four valid values: ``"delete"``, ``"rename"``, ``"reuse"``, or ``"quit"``.  The behavior for each of these values is as follows:

   * **"delete":** The preexisting directory is deleted and a new directory (having the same name as the original preexisting directory) is created.

   * **"rename":** The preexisting directory is renamed and a new directory (having the same name as the original pre-existing directory) is created. The new name of the preexisting directory consists of its original name and the suffix "_old_YYYYMMDD_HHmmss", where ``YYYYMMDD_HHmmss`` is the full date and time of the rename

   * **"reuse":** This method will keep the preexisting directory intact. However, when the preexisting directory is ``$EXPDIR``, this method will save all old files to a subdirectory ``oldxxx/`` and then populate new files into the ``$EXPDIR`` directory. This is useful to keep ongoing runs uninterrupted; rocotoco ``*db`` files and previous cycles will stay and hence there is no need to manually copy or move ``*db`` files and previous cycles back, and there is no need to manually restart related rocoto tasks failed during the workflow generation process. This method may be best suited for incremental system reuses.

   * **"quit":** The preexisting directory is left unchanged, but execution of the currently running script is terminated. In this case, the preexisting directory must be dealt with manually before rerunning the script.

Detailed Output Messages
--------------------------
These variables are flags that indicate whether to print more detailed messages.

``VERBOSE``: (Default: true)
   Flag that determines whether the experiment generation and workflow task scripts print out extra informational messages. Valid values: ``True`` | ``False``

``DEBUG``: (Default: false)
   Flag that determines whether to print out very detailed debugging messages.  Note that if DEBUG is set to true, then VERBOSE will also be reset to true if it isn't already. Valid values: ``True`` | ``False``

.. _ensemble:

``ensemble:``
======================================

This section describes the valid ``ensemble:`` config settings. 

``DO_ENSEMBLE``: (Default: false)
   Flag that determines whether we are verifying an ensemble forecast. Valid values: ``True`` | ``False``

``NUM_ENS_MEMBERS``: (Default: 0)
   The number of ensemble members, if ``DO_ENSEMBLE`` is set to true. This variable also controls the naming of the ensemble member directories. For example, if ``NUM_ENS_MEMBERS`` is set to 8, the member directories will be named *mem1, mem2, ..., mem8*. This variable is not used unless ``DO_ENSEMBLE`` is set to true.

``ENSMEM_NAMES``: (Default: ``'{% for m in range(ensemble.NUM_ENS_MEMBERS) %}{{ "mem%03d, " % m }}{% endfor %}'``)
   A list of names for the ensemble member names following the format mem001, mem002, etc.

``ENS_TIME_LAG_HRS``: (Default: ``'[ {% for m in range([1,ensemble.NUM_ENS_MEMBERS]|max) %} 0, {% endfor %} ]'``)
   Time lag (in hours) to use for each ensemble member. For a deterministic forecast, this is a one-element array. Default values of array elements are zero.

.. _tropical:

``tropical:``
======================================

This section describes the valid ``tropical:`` config settings. These settings (in addition to task-specific settings, see later sections) control behavior of tropical cyclone verification. 

``BASIN``: (Default: ``"AL"``)
   Two-character indicator of the tropical cyclone basin. Valid basins are listed in the `MET users guide <https://metplus.readthedocs.io/projects/met/en/latest/Users_Guide/config_options_tc.html#basin>`_

``STORM_IDS``: (Default: ``[ 00 ]``)
   AKA "storm numbers", a list of the numerical ID for each storm for which TC verification tasks should be run. Each entry can be specified as a two-digit numerical string or an integer. This must be specified in each experiment's config_vx.yaml; the default value '00' is invalid.

``ADECK_DIR``: (Default: ``'{{ verification.VX_FCST_INPUT_BASEDIR }}'``)
   The directory where "a-deck" forecast track files can be found. For more information on these files see `the RAL hurricanes page <https://hurricanes.ral.ucar.edu/realtime/index.php#about_adecks>`_

``ADECK_TEMPLATE``: (Default: ``"{cyclone}l.{init?fmt=%Y%m%d%H}.hfsa.trak.atcfunix"``)
   Format for A-deck forecast track file name. The {cyclone} and {init?fmt=%Y%m%d%H} templates are filled in by METplus at runtime; see the `METplus Users Guide <https://metplus.readthedocs.io/en/latest/Users_Guide/systemconfiguration.html#directory-and-filename-template-info>`_ for more info.

``MODEL``: (Default: ``"HFSA"``)
   The identifier for the forecast data to use for TCPAIRS and TCSTAT comparison. Valid options are 'HFSA' (HAFS-A) and 'HFSB' (HAFS-B).


-.. _VXParams:

``verification:``
=================================

This section describes the valid ``verification:`` config settings. These settings (in addition to task-specific settings, see later sections) control behavior of various verification tasks.

.. _GeneralVXParams:

General VX Parameters
---------------------------------

``VX_FIELD_GROUPS``: (Default: [ "APCP", "REFC", "RETOP", "SFC", "UPA" ])
  The groups of fields (some of which may consist of only a single field) on which
  to run verification. Valid values:
  ``"AOD"`` |``"APCP"`` | ``"ASNOW"`` | ``"GOESADP"`` | ``"GOESAOD"`` | ``"PM10"`` | ``"PM25"`` | ``"REFC"`` | ``"RETOP"`` | ``"SFC"`` | ``"UPA"``

``VX_APCP_ACCUMS_HRS``: (Default: [ 1, 3, 6, 24 ])
   The accumulation intervals (in hours) to include in the verification of
   accumulated precipitation (APCP).  If ``VX_FIELD_GROUPS`` contains ``"APCP"``,
   then ``VX_APCP_ACCUMS_HRS`` must contain at least one element.  Otherwise,
   ``VX_APCP_ACCUMS_HRS`` will be ignored.  Valid values: ``1`` | ``3`` | ``6`` | ``24``

``VX_ASNOW_ACCUMS_HRS``: (Default: [ 6, 24 ])
   The accumulation intervals (in hours) to include in the verification of
   accumulated snowfall (ASNOW).  If ``VX_FIELD_GROUPS`` contains ``"ASNOW"``,
   then ``VX_ASNOW_ACCUMS_HRS`` must contain at least one element.  Otherwise,
   ``VX_ASNOW_ACCUMS_HRS`` will be ignored.  Valid values: ``6`` | ``12`` | ``18`` | ``24``

``VX_CONFIG_[DET|ENS]_FN``: (Default: ``vx_configs/vx_config_[det|ens].yaml``)
   Names of configuration files for deterministic and ensemble verification
   that specify the field groups, field names, levels, and (if applicable)
   thresholds for which to run verification.  These are relative to the
   directory ``METPLUS_CONF`` in which the METplus config templates are
   located.  They may include leading relative paths before the file
   names, e.g. ``some_dir/another_dir/vx_config_det.yaml``.

``VX_OUTPUT_BASEDIR``: (Default: ``'{{ workflow.EXPTDIR }}'``)
   Template for base (i.e. top-level) directory in which METplus will place
   its output.


METplus-Specific Parameters
-----------------------------------

``METPLUS_VERBOSITY_LEVEL``: (Default: ``2``)
   Logging verbosity level used by METplus verification tools. Valid values: 0 to 9, with 0 having the fewest log messages and 9 having the most. Levels 5 and above can result in very large log files and slower tool execution.


VX Parameters for Observations
-------------------------------------

.. note::

   The observation types that the SRW App can currently retrieve (if necessary)
   and use in verification are:

      * CCPA (Climatology-Calibrated Precipitation Analysis)
      * NOHRSC (National Operational Hydrologic Remote Sensing Center)
      * MRMS (Multi-Radar Multi-Sensor)
      * NDAS (NAM Data Assimilation System)
      * AERONET (Aerosol Robotic Network)
      * AIRNOW (AirNow air quality reports)
      * GOESAOD (GOES satellite Aerosol Optical Depth)
      * GOESADP (GOES satellite Aerosol Detection Product)

   The script ``ush/get_obs.py`` contains further details on the files and
   directory structure of each obs type.

``[CCPA|NOHRSC|MRMS|NDAS|AERONET|AIRNOW|GOESAOD|GOESADP]_OBS_AVAIL_INTVL_HRS``: (Defaults: [1|6|1|1|1|1|1|1])
  Time interval (in hours) at which the various types of obs are available
  in the default location (see ``OBS_DATA_STORE_`` variables)

  Note that MRMS and GOES files are in fact available every few minutes, but here
  we set the obs availability interval to 1 hour because verification of sub-hourly forecast output is not yet supported.

``[CCPA|NOHRSC|MRMS|NDAS|AERONET|AIRNOW|GOESAOD|GOESADP]_OBS_DIR``: (Default: ``"{{ workflow.EXPTDIR }}/obs_data/[ccpa|nohrsc|mrms|ndas|aeronet|airnow|goesaod|goesadp]"``)
   Base directory in which CCPA, NOHRSC, MRMS, NDAS, AERONET, AIRNOW, or GOES obs files needed by
   the verification tasks are located.  If the files do not exist, they
   will be retrieved and placed under this directory.  Note that:

   * If the obs files need to be retrieved (e.g. from NOAA's HPSS), because
     they are not already staged on disk, then the user must have write
     permission to this directory.  Otherwise, the ``get_obs`` workflow 
     tasks that attempt to create these files will fail.

   * CCPA obs contain errors in the metadata for a certain range of dates
     that need to be corrected during obs retrieval.  This is described
     in more detail in the script ``ush/get_obs.py``.

``OBS_[CCPA|NOHRSC|MRMS|NDAS|AERONET|AIRNOW|GOESAOD|GOESADP]_FN_TEMPLATES``:
     **Defaults:**

     ``OBS_CCPA_FN_TEMPLATES``:
        .. code-block:: console

           [ 'APCP',
           '{valid?fmt=%Y%m%d}/ccpa.t{valid?fmt=%H}z.{{ "%02d" % verification.CCPA_OBS_AVAIL_INTVL_HRS }}h.hrap.conus.gb2']

     ``OBS_NOHRSC_FN_TEMPLATES``:
        .. code-block:: console

           [ 'ASNOW',
             'sfav2_CONUS_{{ verification.NOHRSC_OBS_AVAIL_INTVL_HRS }}h_{valid?fmt=%Y%m%d%H}_grid184.grb2' ]

     ``OBS_MRMS_FN_TEMPLATES``:
        .. code-block:: console

           [ 'REFC', '{valid?fmt=%Y%m%d}/MergedReflectivityQCComposite_00.50_{valid?fmt=%Y%m%d}-{valid?fmt=%H%M%S}.grib2',
             'RETOP', '{valid?fmt=%Y%m%d}/EchoTop_18_00.50_{valid?fmt=%Y%m%d}-{valid?fmt=%H%M%S}.grib2' ]

     ``OBS_NDAS_FN_TEMPLATES``:
        .. code-block:: console

           [ 'SFCandUPA', 'prepbufr.ndas.{valid?fmt=%Y%m%d%H}' ]

     ``OBS_AERONET_FN_TEMPLATES``:
        .. code-block:: console

           [ 'AOD', '{valid?fmt=%Y%m%d}/{valid?fmt=%Y%m%d}.lev15' ]

     ``OBS_AIRNOW_FN_TEMPLATES``:
        .. code-block:: console

           [ 'PM', '{valid?fmt=%Y%m%d}/HourlyData_{valid?fmt=%Y%m%d%H}.dat' ]

     ``OBS_GOESAOD_FN_TEMPLATES``:
        .. code-block:: console

           [ 'GOESAOD', '{valid?fmt=%Y%m%d}/OR_ABI-L2-AODF_G16_{valid?fmt=%Y%m%d%H}.nc' ]

     ``OBS_GOESADP_FN_TEMPLATES``:
        .. code-block:: console

           [ 'GOESADP', '{valid?fmt=%Y%m%d}/OR_ABI-L2-ADPF_G16_{valid?fmt=%Y%m%d%H}.nc' ]

   File name templates for various obs types.  These are meant to be used
   in METplus configuration files and thus contain METplus time formatting
   strings.  Each of these variables is a python list containing pairs of
   values.  The first element of each pair specifies the verification field
   group(s) for which the file name template will be needed, and the second
   element is the file name template itself, which may include a leading
   relative directory.  (Here, by "verification field group", we mean a
   group of fields that is verified together in the workflow; see the
   description of the variable ``VX_FIELD_GROUPS``.)  For example, for CCPA
   obs, the variable name is ``OBS_CCPA_FN_TEMPLATES``.  From the default value
   of this variable given above, we see that if ``CCPA_OBS_AVAIL_INTVL_HRS``
   is set to 1 (i.e. the CCPA obs are assumed to be available every hour)
   and the valid time is 2024042903, then the obs file (including a relative
   path) to look for and, if necessary, create is

       ``20240429/ccpa.t03z.01h.hrap.conus.gb2``

   This file will be used in the verification of fields under the APCP
   field group (which consist of accumulated precipitation for the
   accumulation intervals specified in ``VX_APCP_ACCUMS_HRS``).

   Note that:

   * The file name templates are relative to the obs base directories given in
     the variables

         ``[CCPA|NOHRSC|MRMS|NDAS]_OBS_DIR``

     defined above.  Thus, the template for the full path to the obs files
     is given, e.g. for CCPA obs, by

         .. code-block:: console

            CCPA_OBS_DIR/OBS_CCPA_FN_TEMPLATES[1]

     where the ``[1]`` indicates the second element of the list ``OBS_CCPA_FN_TEMPLATES``.

   * The file name templates may represent file names only, or they may
     include leading relative directories.

   * The default values of these variables for the CCPA, NOHRSC, and NDAS
     obs types contain only one pair of values (because these obs types
     contain only one set of files that we use in the verification) while
     the default value for the MRMS obs type contains two pairs of values,
     one for the set of files that contains composite reflectivity data
     and another for the set that contains echo top data.  This is simply
     because the MRMS obs type does not group all its fields together into
     one set of files as does, for example, the NDAS obs type.

   * Each file name template must contain full information about the year,
     month, day, and hour by including METplus time formatting strings for
     this information.  Some of this information (e.g. the year, month,
     and day) may be in the relative directory portion of the template and
     the rest (e.g. the hour) in the file name, or there may be no relative
     directory portion and all of this information may be in the file name,
     but all four pieces of timing information must be present somewhere in
     each template as METplus time formatting strings.  If not, obs files
     created by the ``get_obs`` tasks for different days might overwrite each
     other.

   * The workflow generation scripts create a ``get_obs`` task for each obs
     type that is needed in the verification and for each day on which that
     obs type is needed at at least some hours.  That ``get_obs`` task first
     checks whether all the necessary obs files for that day already exist
     at the locations specified by the full path template(s) (which are
     obtained by combining the base directories [CCPA|NOHRSC|MRMS|NDAS]_OBS_DIR
     with the file name template(s)).  If for a given day one or more of
     these obs files do not exist on disk, the ``get_obs`` task will retrieve
     "raw" versions of these files from a data store (e.g. NOAA's HPSS)
     and will place them in a temporary "raw" directory.  It will then
     move or copy these raw files to the locations specified by the full
     path template(s).

   * The raw obs files, i.e. the obs files as they are named and arranged
     in the data stores and retrieved and placed in the raw directories,
     may be arranged differently and/or have names that are different from
     the ones specified in the file name templates.  If so, they are renamed
     while being moved or copied from the raw directories to the locations
     specified by the full path template(s).  (The lists of templates for
     searching for and retrieving files from the data stores is different
     than the METplus templates described here; the former are given in
     the data retrieval configuration file at ``parm/data_locations.yml``.)

   * When the run scripts for the various vx tasks are converted from bash
     to python scripts, these variables should be converted from python
     lists to python dictionaries, where the first element of each pair
     becomes the key and the second becomes the value.  This currently
     cannot be done due to limitations in the workflow on converting
     python dictionaries to bash variables.

``REMOVE_RAW_OBS_DIRS``: (Default: ``True``)
   Flag specifying whether to remove the "raw" observation directories
   after retrieving the specified type of obs (CCPA, NOHRSC, MRMS, or
   NOHRSC) from a data store (e.g. NOAA's HPSS).  The raw directories
   are the ones in which the observation files are placed immediately
   after pulling them from the data store but before performing any
   processing on them such as renaming the files and/or reorganizing
   their directory structure.

``OBS_CCPA_APCP_FN_TEMPLATE_PCPCOMBINE_OUTPUT``:
   **Default:**

   .. code-block:: console

      ccpa.hrap.conus.${FIELD_GROUP}${ACCUM_HH}h.{valid?fmt=%Y%m%d%H?shift=-${ACCUM_HH}H}_to_{valid?fmt=%Y%m%d%H}.nc

   METplus template for the names of the NetCDF files generated by the
   workflow verification tasks that call METplus's PcpCombine tool on
   CCPA observations.  These files will contain observed accumulated
   precipitation in NetCDF format for various accumulation intervals.

``OBS_NOHRSC_ASNOW_FN_TEMPLATE_PCPCOMBINE_OUTPUT``: 
   **Default:**

   .. code-block:: console

      sfav2_CONUS_{{ "%d" % NOHRSC_OBS_AVAIL_INTVL_HRS }}h_{valid?fmt=%Y%m%d%H}_grid184.grb2_a${ACCUM_HH}h.nc

   METplus template for the names of the NetCDF files generated by the
   workflow verification tasks that call METplus's PcpCombine tool on
   NOHRSC observations.  These files will contain observed accumulated
   snowfall for various accumulation intervals.

``OBS_AERONET_FN_TEMPLATE_ASCII2NC_OUTPUT``: (Default: ``'hourly_aeronet_obs_{valid?fmt=%Y%m%d}00.nc'``)
   
   METplus template for the names of the NetCDF files generated by the
   workflow verification tasks that call METplus's ASCII2NC tool on
   AERONET observations.

``OBS_AIRNOW_FN_TEMPLATE_ASCII2NC_OUTPUT``: (Default: ``'hourly_airnow_obs_{valid?fmt=%Y%m%d}00.nc'``)
   
   METplus template for the names of the NetCDF files generated by the
   workflow verification tasks that call METplus's ASCII2NC tool on
   AIRNOW observations.  

``AIRNOW_INPUT_FORMAT``: (Default: ``"airnowhourlyaqobs"``)
   Observation format for ASCII Airnow observations. Observations retrieved from HPSS are in
   "airnowhourlyaqobs" format, observations retrieved from AWS are generally in "airnowhourly" format.
   For more information see the
   `METplus users guide <https://metplus.readthedocs.io/projects/met/en/latest/Users_Guide/reformat_point.html#ascii2nc-tool>`_

``FCST_SMOKE_TYPE``: (Default: ``RRFS``)
   Different forecast model data have different particulate matter variables that must be verified differently
   with AIRNOW observations.  Valid options are ``RRFS`` and ``HRRR``.

``OBS_DATA_STORE_[CCPA|NOHRSC|MRMS|NDAS|AERONET|AIRNOW|GOESAOD|GOESADP]``: (Defaults: ``[hpss|hpss|hpss|hpss|hpss|hpss|aws|aws]``)
   Data repository to retrieve observation data from. Valid values are "aws" and/or "hpss", see
   ``parm/data_locations.yaml`` for info on these data stores.

``OBS_NDAS_SFCandUPA_FN_TEMPLATE_PB2NC_OUTPUT``: (Default: ``'{{ verification.OBS_NDAS_FN_TEMPLATES[1] }}.nc'``)
   METplus template for the names of the NetCDF files generated by the
   workflow verification tasks that call METplus's Pb2nc tool on the 
   prepbufr files in NDAS observations.  These files will contain the
   observed surface (SFC) and upper-air (UPA) fields in NetCDF format
   (instead of NDAS's native prepbufr format).

``NUM_MISSING_OBS_FILES_MAX``: (Default: 0)
   For verification tasks that need observational data, this specifies
   the maximum number of observation files that may be missing.  If more
   than this number are missing, the verification task will error out.


VX Parameters for Forecasts
----------------------------------

``VX_FCST_MODEL_NAME``: (Default: ``'srw'``)
   String that specifies a descriptive name for the model being verified.
   This is used in forming the names of the verification output files and
   is also included in the contents of those files.

``VX_FCST_OUTPUT_INTVL_HRS``: (Default: 1)
   The forecast output interval (in hours) to assume for verification
   purposes.

``VX_FCST_INPUT_BASEDIR``: (Default: ``'{{ workflow.EXPTDIR }}'``)
   METplus template for the name of the base (i.e. top-level) directory
   containing the forecast files to use as inputs to the verification
   tasks.

``FCST_FN_TEMPLATE``: (Default: ``'srw.t{init?fmt=%H?shift=-${time_lag}}z.prslev.f{lead?fmt=%HHH?shift=${time_lag}}.{{ verification.VX_FCST_MODEL_NAME }}.grib2'``)
   METplus template for the names of the forecast files to use as inputs
   to the verification tasks. Can include subdirectories if needed.

``FCST_FN_TEMPLATE_PCPCOMBINE_OUTPUT``:
   **Default:**

   .. code-block:: console
 
      srw.t{init?fmt=%H}z.prslev.{{ verification.VX_FCST_MODEL_NAME }}.${FIELD_GROUP}${ACCUM_HH}h.{valid?fmt=%Y%m%d%H?shift=-${ACCUM_HH}H}_to_{valid?fmt=%Y%m%d%H}.nc

   METplus template for the names of the NetCDF files generated by the
   workflow verification tasks that call METplus's PcpCombine tool on
   forecast output.  These files will contain forecast accumulated
   precipitation in NetCDF format for various accumulation intervals.

``VX_NDIGITS_ENSMEM_NAMES``: (Default: 3)
   Number of digits to assume/use in the forecast ensemble member identifier
   string used in directory and file names and other instances in which the
   ensemble member needs to be identified.  For example, if this is set to
   3, the identifier for ensemble member 4 will be "mem004", while if it's
   set to 2, the identifier will be "mem04".  This is useful when verifying
   staged forecast files from a forecasting model/system other than the
   SRW that uses a different number of digits in the ensemble member 
   identifier string.

``NUM_MISSING_FCST_FILES_MAX``: (Default: 0)
   For verification tasks that need forecast data, this specifies the
   maximum number of post-processed forecast files that may be missing. 
   If more than this number are missing, the verification task will exit
   with an error.

``VX_MASK``: (Default: [])
   Name(s) of the sub-grid(s) of the forecast domain to verify on. Valid grids are found in the
   `MET Users Guide <https://metplus.readthedocs.io/projects/met/en/latest/Users_Guide/appendixB.html#grids>`__
   or under ``dtc-vx-workflow/parm/metplus/GRIDNAME.poly``. Users can also include custom verification domains
   by adding their own ``GRIDNAME.poly`` files in that location. A script for visualizing these custom domains,
   ``dtc-vx-workflow/parm/metplus/plot_met_poly_points.py``, is also included.

``VX_TASKS``: (Default: 1)
   Number of verification tasks to run in parallel; this works for METplus tools that work on
   sequential forecast hours, and so can be run simultaneously.



Task-specific sections
===================

The following sections of the config file all apply to a specific workflow task, which usually runs a single MET/METplus task.
Unlike the above sections, each of these sections contains an ``execution:`` subsection where runtime settings for that particular job can be set.

.. _point2grid:

``point2grid:``
----------------------------------

This section describes the valid ``point2grid:`` config settings.

``execution:``
   ``tasks_per_node``: (Default: ``'{{ point2grid.TASKS }}'``)

   ``walltime``: (Default: ``'01:00:00'``)

   ``memory``: (Default: ``'{{ 2 * point2grid.TASKS }}G'``)

``REGRID_METHOD``: (Default: ``'BILIN'``)
   The method to interpolate point observations to the specified grid.

``GOES_QC_FLAGS``: (Default: ``'0,1'``)
  Comma-separated string indicating which DQF (quality control) flags to keep for GOES observations. Described in GOES_ABI_products_PUG-L2+-vol5.pdf 

  * 0: high quality
  * 1: medium quality
  * 2: low quality
  * 3: no retrieval quality flag

``TASKS``: (Default: 1)
   The number of Point2Grid instances to run in parallel

.. _regriddataplane:

``regriddataplane:``
----------------------------------

This section describes the valid ``regriddataplane:`` config settings.

``execution:``
   ``tasks_per_node``: (Default: ``'{{ regriddataplane.TASKS }}'``)
       
   ``walltime``: (Default: ``'00:30:00'``)

   ``memory``: (Default: ``'{{ 10 * regriddataplane.TASKS }}G'``)

``TASKS``: (Default: 1)
   The number of RegridDataPlane instances to run in parallel

``REGRID_METHOD``: (Default: ``MAXGAUSS``)
   Regridding method. See https://metplus.readthedocs.io/projects/met/en/latest/Users_Guide/reformat_grid.html#optional-arguments-for-regrid-data-plane for valid options

``GAUSSIAN_DX``: (Default: 81.271)
   Overrides default settings for Gaussian smoothing. Only used if REGRID_METHOD=MAXGAUSS

``GAUSSIAN_RADIUS``: (Default: 120)
   Overrides default settings for Gaussian smoothing. Only used if REGRID_METHOD=MAXGAUSS



.. _mode: 

``mode:``
----------------------------
     
This section describes the valid ``mode:`` config settings.
     
``execution:``
   ``tasks_per_node``: (Default: ``'{{ mode.TASKS }}'``)
       
   ``walltime``: (Default: ``'01:00:00'``)

   ``memory``: (Default: ``'{{ 10 * mode.TASKS }}G'``)

``TASKS``: (Default: 1)
   The number of MODE instances to run in parallel

``CONV_RADIUS``: (Default: ``[ 5 ]``)
   The radius of a circular convolution applied to the raw fields for defining MODE objects. This variable is a list, as multiple convolutional radii may be specified.

``CONV_THRESH``: (Default: ``['>=0']``)
  
  The value threshold defining what consitutes an object. Multiple values may be specified for multiple output convolutions. The threshold used should depend on the observation type; for example, 20, 30, or 40 (dBZ) are typically used for radar reflectivity.

``MERGE_FLAG``: (Default: ``'NONE'``)
  
  The merging techinque to use for MODE objects. Valid values are NONE, THRESH, ENGINE, or BOTH

``MERGE_THRESH``: (Default: ``['>=5']``)
   
  The threshold value(s) to be applied to the convolved field to define objects. Larger values will result in larger/more-merged objects. Should be the same length as ``CONV_THRESH``. No effect unless MERGE_FLAG=``THRESH`` or ``BOTH``

``GRID_RES``: (Default: ``0``)
   
  Nominal grid resolution in kilometers.

``TOTAL_INTEREST_THRESH``: (Default: ``0.7``)
   
  A value between 0 and 1 that controls how MODE objects are matched. Higher values will increase the strictness of the comparison (decreasing the number of matches), and vice versa

``OUTPUT_TEMPLATE``: (Default: ``'MODE_GOESAOD_{init?fmt=%Y%m%d%H}'``)
   
  Template for MODE output filenames

.. _tcpairs:

``tcpairs:``
----------------------------

This section describes the valid ``tcpairs:`` config settings.

``execution:``
   ``tasks_per_node``: (Default: ``1``)

   ``walltime``: (Default: ``'00:10:00'``)

   ``memory``: (Default: ``'2G'``)

``TECH_ID_VX``: (Default: ``'OFCL'``)

  The identifier for the best track data to use for TCPAIRS comparison, as read in from the ATCF-format input file. Valid values are documented here: https://ftp.nhc.noaa.gov/atcf/docs/nhc_techlist.dat

``OUTPUT_TEMPLATE``: (Default: ``'tc_pairs.{{ tropical.MODEL }}.{{ tropical.BASIN }}{cyclone}{init?fmt=%Y}'``)

  Template for output file(s) from TCPAIRS. ``{basin}``, ``{cyclone}``, and ``{init}`` are substituted in the METplus process, not in the workflow. The final filename will have the ".tcst" extension added to it

.. _tcstat:

``tcstat:``
----------------------------

This section describes the valid ``tcstat:`` config settings.

``execution:``
   ``tasks_per_node``: (Default: ``1``)

   ``walltime``: (Default: ``'00:10:00'``)

   ``memory``: (Default: ``'2G'``)

``SUMMARY_FILE``: (Default: ``'tc_stat_summary.{{ tropical.MODEL }}.{{ tropical.BASIN }}{cyclone}_{init?fmt=%Y}.tcst'``)

  Filename for TCstat summary output

``RI_FILE``: (Default: ``'tc_rirw.{{ tropical.MODEL }}.{{ tropical.BASIN }}{cyclone}_{init?fmt=%Y}.tcst'``)

  Filename for TCstat rapid intensification statistics output

.. _tcrmw:

``tcrmw:``
----------------------------

This section describes the valid ``tcrmw:`` config settings.

``execution:``
   ``tasks_per_node``: (Default: ``1``)

   ``walltime``: (Default: ``'00:30:00'``)

   ``memory``: (Default: ``'2G'``)

``OUTPUT_TEMPLATE``: (Default: ``'tc_rmw_{{ tropical.MODEL }}.{{ tropical.BASIN }}{cyclone}{date?fmt=%Y}.nc'``)

  Template for output file(s) from TCRMW. ``{cyclone}`` and ``{date}`` are substituted in the METplus process, not in the workflow.




