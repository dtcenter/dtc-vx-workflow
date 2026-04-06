.. _Testing:

===========================
Testing the DTC VX Workflow
===========================

Workflow End-to-End (WE2E) Tests
==================================================

The verification workflow contains a set of end-to-end tests that exercise various workflow configurations for verification tests with different sets of input observations, model data, METplus tools, verification metrics, ensemble members, and other settings. These are referred to as workflow end-to-end (WE2E) tests because they all use the Rocoto workflow manager to run their individual workflows from start to finish. The purpose of these tests is to ensure that new changes to the workflow do not break existing functionality and capabilities. However, these WE2E tests also provide users with example cases to help configure the workflow, including staged data.

.. attention::

   * This introductory section provides high-level information on what is and is not tested with WE2E tests. It also provides information on :ref:`WE2E test categories <we2e-categories>` and the :ref:`WE2E test information file <WE2ETestInfoFile>`, which summarizes each test. 
   * To skip directly to running WE2E tests, go to :numref:`Section %s: Running the WE2E Tests <RunWE2E>`.

What is a WE2E test?
----------------------

WE2E tests are, in essence, tests of the workflow generation, task execution (:term:`J-jobs`, 
:term:`ex-scripts`), and other auxiliary scripts to ensure that these scripts function correctly. Tested functions
include creating and correctly arranging and naming directories and files, ensuring 
that all input files are available and readable, running tasks with correct configuration options, etc. 

Note that the WE2E tests are **not** regression tests---they do not check whether 
current results are identical to previously established baselines. They also do
not test the scientific integrity of the results (e.g., they do not check that values 
of output fields are reasonable). These tests only check that the tasks within each test's workflow complete successfully.
However, we do have plans to implement true regression testing in the future.

.. _we2e-categories:

WE2E Test Categories
----------------------

For convenience, the WE2E tests are currently grouped into the following categories (under ``dtc-vx-workflow/tests/WE2E/test_configs/``):

* ``deterministic``
   This category contains the most basic tests, for deterministic verification with various forecast and observation types.

* ``ensemble``
   This category tests configurations of ensemble forecast verification, including a time-lagged ensemble case.

* ``MODE``
   This category for object-based verification using MODE.

* ``tc``
   This category tests various tropical-cyclone specific verification tasks.

.. note::

   Users should be aware that some tests assume :term:`HPSS` access. We are working on removing this requirement using alternative data sources. 
   

.. _RunWE2E:

Running the WE2E Tests
----------------------

About the Test Script (``run_we2e_tests.py``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The script to run the WE2E tests is named ``run_we2e_tests.py`` and is located in the directory ``dtc-vx-workflow/tests/WE2E``. Each WE2E test has an associated configuration file named ``config.${test_name}.yaml`` in the ``test_configs`` directory, where ``${test_name}`` is the name of the corresponding test. These configuration files are subsets of the full range of ``config.yaml`` experiment configuration options. (See :numref:`Section %s <ConfigWorkflow>` for all configurable options and :numref:`Section %s <UserSpecificConfig>` for information on configuring ``config.yaml`` or any test configuration ``.yaml`` file.) For each test, the ``run_we2e_tests.py`` script reads in the test configuration file and generates from it a complete ``config.yaml`` file. It then calls the ``generate_wflow()`` function from ``dtc-vx-workflow/ush/generate_wflow.py``, which in turn reads in ``config.yaml`` and generates a new experiment for the test. The name of each experiment directory is set to that of the corresponding test, and a copy of ``config.yaml`` for each test is placed in its experiment directory.


Using the Test Script 
^^^^^^^^^^^^^^^^^^^^^

First, load the appropriate python environment (as described in :numref:`Section %s <SetUpPythonEnv>`).

The test script has three required arguments: machine, account, and tests. 

   * Users must indicate which machine they are on using the ``--machine`` or ``-m`` option. See :numref:`Section %s <user>` for valid values or check the ``valid_param_vals.yaml`` file.
   * Users must submit a valid account name using the ``--account`` or ``-a`` option to run submitted jobs. On systems where an account name is not required, users may simply use ``-a none``. 
   * Users must specify the set of tests to run using the ``--tests`` or ``-t`` option. Users may pass (in order of priority): 

      #. The name of a single test or list of tests to the test script. 
      #. The name of a subdirectory under ``dtc-vx-workflow/tests/WE2E/test_configs/`` 
      #. The name of a text file (full or relative path), such as ``my_tests.txt``, which contains a list of the WE2E tests to run (one per line).
      #. "all" to run all tests 

Users may run ``./run_we2e_tests.py -h`` for additional (optional) usage instructions. 

Examples
^^^^^^^^^^^

.. attention::

   * Users will need to adjust the machine name and account in these examples to run tests successfully. 
   * These commands assume that the user is working from the ``WE2E`` directory (``dtc-vx-workflow/tests/WE2E/``). 

To run the ``MET_verification`` and ``MODE_AOD`` tests on Hercules, users could run: 

.. code-block:: console

   ./run_we2e_tests.py -m hercules --account gsd-fv3-test -t MET_verification MODE_AOD

Alternatively, to run the entire set of ensemble tests on Hera, users might run: 

.. code-block:: console

   ./run_we2e_tests.py -t ensemble -m hera -a nems

By default, the experiment directory for a WE2E test has the same name as the test itself, and it is created in ``${HOMEdir}/../expt_dirs``, where ``HOMEdir`` is the top-level directory for the ``dtc-vx-workflow`` repository (usually set to something like ``/path/to/dtc-vx-workflow``). Thus, the ``MET_verification_smoke_only_vx`` experiment directory would be located in ``${HOMEdir}/../expt_dirs/MET_verification_smoke_only_vx``.

**A More Complex Example:** To run the fundamental suite of tests on Orion in parallel, charging computational resources to the "gsd-fv3" account, and placing all the experiment directories into a directory named ``test_set_01``, run:

   .. code-block::

      ./run_we2e_tests.py -t deterministic -m orion -a gsd-fv3 --expt_basedir "test_set_01" -q -p 2

   * ``--expt_basedir``: Useful for grouping sets of tests. If set to a relative path, the provided path will be appended to the default path. In this case, all of the fundamental tests will reside in ``${HOMEdir}/../expt_dirs/test_set_01/``. It can also take a full (absolute) path as an argument, which will place experiments in the given location.
   * ``-q``: Suppresses the output from ``generate_wflow()`` and prints only important messages (warnings and errors) to the screen. The suppressed output will still be available in the ``log.run_WE2E_tests`` file.
   * ``-p 2``: Indicates the number of parallel proceeses to run. By default, job monitoring and submission is serial, using a single task. Therefore, the script may take a long time to return to a given experiment and submit the next job when running large test suites. Depending on the machine settings, running in parallel can substantially reduce the time it takes to run all experiments. However, it should be used with caution on shared resources (such as HPC login nodes) due to the potential to overwhelm machine resources. 

Workflow Information
^^^^^^^^^^^^^^^^^^^^^^

For each specified test, ``run_we2e_tests.py`` will generate a new experiment directory and, by default, launch a second function ``monitor_jobs()`` that will continuously monitor active jobs, submit new jobs, and track the success or failure status of the experiment in a ``.yaml`` file. Finally, when all jobs have finished running (successfully or not), the function ``print_WE2E_summary()`` will print a summary of the jobs to screen, including the job's success or failure, timing information, and (if on an appropriately configured platform) the number of core hours used. An example run would look like this: 

.. code-block:: console

   $ ./run_we2e_tests.py -t my_tests.txt -m hera -a gsd-fv3 -q
   Checking that all tests are valid
   Will run 2 tests:
   /user/home/dtc-vx-workflow/tests/WE2E/test_configs/ensemble/config.MET_ensemble_verification.yaml
   /user/home/dtc-vx-workflow/tests/WE2E/test_configs/tc/config.HAFS-A.yaml
   Calling workflow generation function for test MET_ensemble_verification
   ...
   Workflow for test MET_ensemble_verification successfully generated in
   /user/home/expt_dirs/MET_ensemble_verification
   
   Calling workflow generation function for test HAFS-A
   ...
   Workflow for test HAFS-A successfully generated in
   /user/home/expt_dirs/HAFS-A
   
   All experiments have been generated;
   Experiment file WE2E_tests_20260403181012.yaml created
   Writing information for all experiments to WE2E_tests_20260403181012.yaml
   Checking tests available for monitoring...
   Starting experiment MET_ensemble_verification_20260403181001 running
   Starting experiment HAFS-A_20260403181012 running
   Setup complete; monitoring 2 experiments
   Use ctrl-c to pause job submission/monitoring
   Experiment HAFS-A_20260403181012 is COMPLETE
   Took 0:04:10.599122; will no longer monitor.
   Experiment MET_ensemble_verification_20260403181001 is COMPLETE
   Took 0:09:18.945497; will no longer monitor.
   All 2 experiments finished
   Calculating core-hour usage and printing final summary
   ----------------------------------------------------------------------------------------------------
   Experiment name                                                  | Status    | Estimated core hours used 
   ----------------------------------------------------------------------------------------------------
   MET_ensemble_verification_20260403181001                           COMPLETE               0.66
   HAFS-A_20260403181012                                              COMPLETE               0.05
   ----------------------------------------------------------------------------------------------------
   Total                                                              COMPLETE               0.71
   
   Detailed summary written to /user/home/expt_dirs/WE2E_summary_20260403181920.txt



As the script runs, detailed debug output is written to the file ``log.run_WE2E_tests``. This can be useful for debugging if something goes wrong. Adding the ``-d`` flag will print all this output to the screen while the tests run, but this can get quite cluttered on the command line.

The progress of ``monitor_jobs()`` is tracked in a file ``WE2E_tests_{datetime}.yaml``, where {datetime} is the date and time (in ``YYYYMMDDHHmmSS`` format) that the file was created. The final job summary is written by the ``print_WE2E_summary()``; this prints a short summary of experiments to the screen and prints a more detailed summary of all jobs for all experiments in the indicated ``.txt`` file.

.. code-block:: console

   $ cat /user/home/expt_dirs/WE2E_summary_20260403181920.txt
   ----------------------------------------------------------------------------------------------------
   Experiment name                                                  | Status    | Core hours used 
   ----------------------------------------------------------------------------------------------------
   MET_ensemble_verification_20260403181001                           COMPLETE               0.66
   HAFS-A_20260403181012                                              COMPLETE               0.05
   ----------------------------------------------------------------------------------------------------
   Total                                                              COMPLETE               0.71
   
   Detailed summary of each experiment:
   
   ----------------------------------------------------------------------------------------------------
   Detailed summary of experiment MET_ensemble_verification_20260403181001
   in directory /user/home/expt_dirs/MET_ensemble_verification
                                           | Status    | Walltime   | Estimated core hours used
   ----------------------------------------------------------------------------------------------------
   get_obs_ccpa_202105120000                 SUCCEEDED          21.0           0.01
   get_obs_mrms_202105120000                 SUCCEEDED          20.0           0.01
   get_obs_ndas_202105120000                 SUCCEEDED          20.0           0.01
   check_post_output_mem001_202105121200     SUCCEEDED          23.0           0.01
   check_post_output_mem002_202105121200     SUCCEEDED          23.0           0.01
   run_MET_Pb2nc_obs_NDAS_202105120000       SUCCEEDED          32.0           0.01
   run_MET_PcpCombine_APCP01h_obs_CCPA_2021  SUCCEEDED          15.0           0.00
   run_MET_PcpCombine_APCP03h_obs_CCPA_2021  SUCCEEDED          11.0           0.00
   run_MET_PcpCombine_APCP06h_obs_CCPA_2021  SUCCEEDED          12.0           0.00
   run_MET_GenEnsProd_vx_REFC_202105121200   SUCCEEDED          23.0           0.01
   run_MET_GenEnsProd_vx_RETOP_202105121200  SUCCEEDED          23.0           0.01
   run_MET_GenEnsProd_vx_SFC_202105121200    SUCCEEDED          56.0           0.02
   run_MET_GenEnsProd_vx_UPA_202105121200    SUCCEEDED          88.0           0.02
   run_MET_EnsembleStat_vx_REFC_20210512120  SUCCEEDED          66.0           0.02
   run_MET_EnsembleStat_vx_RETOP_2021051212  SUCCEEDED          73.0           0.02
   run_MET_GridStat_vx_REFC_ensprob_2021051  SUCCEEDED         415.0           0.12
   run_MET_GridStat_vx_RETOP_ensprob_202105  SUCCEEDED         482.0           0.13
   run_MET_PcpCombine_APCP01h_fcst_mem001_2  SUCCEEDED          15.0           0.00
   run_MET_PcpCombine_APCP01h_fcst_mem002_2  SUCCEEDED          14.0           0.00
   run_MET_PcpCombine_APCP03h_fcst_mem001_2  SUCCEEDED          12.0           0.00
   run_MET_PcpCombine_APCP03h_fcst_mem002_2  SUCCEEDED          12.0           0.00
   run_MET_PcpCombine_APCP06h_fcst_mem001_2  SUCCEEDED          11.0           0.00
   run_MET_PcpCombine_APCP06h_fcst_mem002_2  SUCCEEDED          10.0           0.00
   run_MET_GridStat_vx_REFC_mem001_20210512  SUCCEEDED          90.0           0.03
   run_MET_GridStat_vx_RETOP_mem001_2021051  SUCCEEDED          98.0           0.03
   run_MET_GridStat_vx_REFC_mem002_20210512  SUCCEEDED          90.0           0.03
   run_MET_GridStat_vx_RETOP_mem002_2021051  SUCCEEDED          97.0           0.03
   run_MET_PointStat_vx_SFC_mem001_20210512  SUCCEEDED          35.0           0.01
   run_MET_PointStat_vx_SFC_mem002_20210512  SUCCEEDED          34.0           0.01
   run_MET_PointStat_vx_UPA_mem001_20210512  SUCCEEDED          48.0           0.01
   run_MET_PointStat_vx_UPA_mem002_20210512  SUCCEEDED          47.0           0.01
   run_MET_GridStat_vx_APCP01h_mem001_20210  SUCCEEDED          10.0           0.00
   run_MET_GridStat_vx_APCP01h_mem002_20210  SUCCEEDED           9.0           0.00
   run_MET_GridStat_vx_APCP03h_mem001_20210  SUCCEEDED           8.0           0.00
   run_MET_GridStat_vx_APCP03h_mem002_20210  SUCCEEDED           7.0           0.00
   run_MET_GridStat_vx_APCP06h_mem001_20210  SUCCEEDED           6.0           0.00
   run_MET_GridStat_vx_APCP06h_mem002_20210  SUCCEEDED           6.0           0.00
   run_MET_GenEnsProd_vx_APCP01h_2021051212  SUCCEEDED          18.0           0.01
   run_MET_GenEnsProd_vx_APCP03h_2021051212  SUCCEEDED          13.0           0.00
   run_MET_GenEnsProd_vx_APCP06h_2021051212  SUCCEEDED          11.0           0.00
   run_MET_EnsembleStat_vx_SFC_202105121200  SUCCEEDED          52.0           0.01
   run_MET_PointStat_vx_SFC_ensmean_2021051  SUCCEEDED          31.0           0.01
   run_MET_PointStat_vx_SFC_ensprob_2021051  SUCCEEDED          46.0           0.01
   run_MET_EnsembleStat_vx_APCP03h_20210512  SUCCEEDED          16.0           0.00
   run_MET_EnsembleStat_vx_APCP06h_20210512  SUCCEEDED          13.0           0.00
   run_MET_GridStat_vx_APCP03h_ensmean_2021  SUCCEEDED          11.0           0.00
   run_MET_GridStat_vx_APCP06h_ensmean_2021  SUCCEEDED          10.0           0.00
   run_MET_GridStat_vx_APCP03h_ensprob_2021  SUCCEEDED          13.0           0.00
   run_MET_GridStat_vx_APCP06h_ensprob_2021  SUCCEEDED          11.0           0.00
   run_MET_EnsembleStat_vx_APCP01h_20210512  SUCCEEDED          31.0           0.01
   run_MET_GridStat_vx_APCP01h_ensmean_2021  SUCCEEDED          15.0           0.00
   run_MET_GridStat_vx_APCP01h_ensprob_2021  SUCCEEDED          20.0           0.01
   run_MET_EnsembleStat_vx_UPA_202105121200  SUCCEEDED          35.0           0.01
   run_MET_PointStat_vx_UPA_ensmean_2021051  SUCCEEDED          31.0           0.01
   run_MET_PointStat_vx_UPA_ensprob_2021051  SUCCEEDED          38.0           0.01
   ----------------------------------------------------------------------------------------------------
   Total                                     COMPLETE                          0.66
   
   ----------------------------------------------------------------------------------------------------
   Detailed summary of experiment HAFS-A_20260403181012
   in directory /user/home/expt_dirs/HAFS-A
                                           | Status    | Walltime   | Estimated core hours used
   ----------------------------------------------------------------------------------------------------
   tcpairs_202309051200                      SUCCEEDED          12.0           0.00
   tcstat_202309051200                       SUCCEEDED           6.0           0.00
   tcrmw_202309051200                        SUCCEEDED         183.0           0.05
   ----------------------------------------------------------------------------------------------------
   Total                                     COMPLETE                          0.05


One might have noticed the line during the experiment run that reads "Use ctrl-c to pause job submission/monitoring". The ``monitor_jobs()`` function (called automatically after all experiments are generated) is designed to be easily paused and re-started if necessary. To stop actively submitting jobs, simply quit the script using ``ctrl-c`` to stop the function, and a short message will appear explaining how to continue the experiment:

.. code-block:: console

   Setup complete; monitoring 1 experiments
   Use ctrl-c to pause job submission/monitoring
   ^C

   User interrupted monitor script; to resume monitoring jobs run:

   ./monitor_jobs.py -y=WE2E_tests_20260331125827.yaml

Checking Test Status and Summary
----------------------------------

By default, ``./run_we2e_tests.py`` will actively monitor jobs, printing to console when jobs are complete (either successfully or with a failure), and printing a summary file ``WE2E_summary_{datetime.now().strftime("%Y%m%d%H%M%S")}.txt``.
However, if the user is using the legacy crontab option (by submitting ``./run_we2e_tests.py`` with the ``--launch cron`` option), or if the user would like to summarize one or more experiments that either are not complete or were not handled by the WE2E test scripts, this status/summary file can be generated manually using ``WE2E_summary.py``.
In this example, an experiment was generated using the crontab option and has not yet finished running.
We use the ``-e`` option to point to the experiment directory and get the current status of the experiment:

.. code-block:: console

   ./WE2E_summary.py -e /user/home/expt_dirs/test1
   ----------------------------------------------------------------------------------------------------
   Experiment name                                              | Status    | Estimated core hours used 
   ----------------------------------------------------------------------------------------------------
   MET_verification                                               RUNNING                0.08
   MET_verification_only_vx                                       COMPLETE               0.09
   MET_verification_smoke_only_vx                                 DYING                  0.05
   MET_verification_winter_wx                                     DEAD                   0.00
   ----------------------------------------------------------------------------------------------------
   Total                                                          DEAD                   0.22
   
   Detailed summary written to /user/home/expt_dirs/test1/WE2E_summary_20260404200815.txt

As with all python scripts in the verification workflow, additional options for this script can be viewed by calling with the ``-h`` argument.

The "Status" as specified by the above summary is explained below:

* ``CREATED``
   The experiment directory has been created, but the monitor script has not yet begun submitting jobs. This is immediately overwritten at the beginning of the "monitor_jobs" function, so this status should not be seen unless the experiment has not yet been started.

* ``SUBMITTING``
   All jobs are in status SUBMITTING or SUCCEEDED (as reported by the Rocoto workflow manager). This is a normal state; we will continue to monitor this experiment.

* ``DYING``
   One or more tasks have died (status "DEAD"), so this experiment has had an error. We will continue to monitor this experiment until all tasks are either status DEAD or status SUCCEEDED (see next entry).

* ``DEAD``
   One or more tasks are at status DEAD, and the rest are either DEAD or SUCCEEDED. We will no longer monitor this experiment.

* ``ERROR``
   Could not read the rocoto database file. This will require manual intervention to solve, so we will no longer monitor this experiment.

* ``RUNNING``
   One or more jobs are at status RUNNING, and the rest are either status QUEUED, SUBMITTED, or SUCCEEDED. This is a normal state; we will continue to monitor this experiment.

* ``QUEUED``
   One or more jobs are at status QUEUED, and some others may be at status SUBMITTED or SUCCEEDED. This is a normal state; we will continue to monitor this experiment.

* ``SUCCEEDED``
   All jobs are status SUCCEEDED; we will monitor for one more cycle in case there are unsubmitted jobs remaining.

* ``COMPLETE``
   All jobs are status SUCCEEDED, and we have monitored this job for an additional cycle to ensure there are no unsubmitted jobs. We will no longer monitor this experiment.

.. _ModExistingTest:

Modifying an Existing WE2E Test
-----------------------------
To modify an existing test, simply edit the configuration file for that test by changing
existing variable values and/or adding new variables to suit the requirements of the
modified test. Such a change may also require modifications to the test description
in the header of the file.


.. _AddNewTest:

Adding a New WE2E Test
---------------------
To add a new test named, e.g., ``new_test01``, to one of the existing test categories, such as ``tc``:

#. Choose an existing test configuration file that most closely matches the new test to be added. It could come from any one of the category directories. 

#. Copy that file to ``config.new_test01.yaml`` and, if necessary, move it to the ``tc`` category directory. 

#. Edit the header comments in ``config.new_test01.yaml`` so that they properly describe the new test.

#. Edit the contents of ``config.new_test01.yaml`` by modifying existing experiment variable values and/or adding new variables such that the test runs with the intended configuration.

.. _UnitTests:
Unit Tests
========================
More info coming soon!
