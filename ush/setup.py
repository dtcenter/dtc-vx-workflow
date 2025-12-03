#!/usr/bin/env python3

"""
Read in the configuration YAMLs and prepare a self-consistent
experiment configuration file.
"""

# pylint: disable=too-many-lines, too-many-branches, logging-fstring-interpolation

import datetime
import logging
import os
import re
import sys
from io import StringIO
from pathlib import Path
from textwrap import dedent


from uwtools.api.config import get_yaml_config, validate
from uwtools.api.template import render

from python_utils import (
    check_for_preexist_dir_file,
)

from set_cycle_and_obs_timeinfo import (
    set_cycle_dates,
    set_fcst_output_times_and_obs_days_all_cycles,
    set_rocoto_cycledefs_for_obs_days,
    check_temporal_consistency_cumul_fields,
    get_obs_retrieve_times_by_day,
)


def load_config_for_setup(ushdir, default_config_path, user_config_path):
    """Load in the default, machine, and user configuration files into
    Python dictionaries. Return the combined experiment dictionary.

    Args:
      ushdir             (str): Path to the ``ush`` directory for the VX workflow
      default_config     (str): Path to ``config_defaults.yaml``
      user_config        (str): Path to the user-provided config YAML (usually named
                                ``config.yaml``)

    Returns:
        The combined, schema-checked experiment Config object.

    Raises:
        FileNotFoundError: If the user-provided configuration file or the machine file does not
                           exist.
        Exception: If (1) the user-provided configuration file cannot be loaded or (2) it contains
                   invalid sections/keys or (3) it does not contain mandatory information or (4)
                   an invalid datetime format is used.
    """
    logger = logging.getLogger(__name__)


    ushdir = Path(ushdir)

    # Load the default and user configs.
    logger.debug(f"Loading config defaults file {default_config_path}")
    default_config = get_yaml_config(default_config_path)
    logger.debug("Read in the following values from config defaults file:\n")
    logger.debug(default_config)

    user_config = get_yaml_config(user_config_path)
    logger.debug(
        f"Read in the following values from YAML config file {user_config}:\n"
    )
    logger.debug(user_config)

    machine = user_config["user"]["MACHINE"].upper()
    user_config["user"]["MACHINE"] = machine

    # Load the machine config file

    machine_file = ushdir / "machine" / f"{machine.lower()}.yaml"

    if not machine_file.exists():
        raise FileNotFoundError(
            dedent(
                f"""
            The machine file {machine_file} does not exist.
            Check that you have specified the correct machine
            ({machine}) in your config file {user_config}"""
            )
        )
    logger.debug(f"Loading machine defaults file {machine_file}")
    machine_config = get_yaml_config(machine_file)


    # Load the rocoto workflow default file
    default_workflow = ushdir.parent / "parm" / "wflow" / "default_workflow.yaml"
    workflow_config = get_yaml_config(default_workflow)

    # Update default config with other loaded config file. Order matters.
    for cfg in (
        workflow_config,
        machine_config,
        user_config,
    ):
        default_config.update_from(cfg)


    # Set the path to the top-level workflow directory
    homedir = Path(__file__).parent.parent.resolve()
    default_config["user"]["HOMEdir"] = str(homedir)

    # Expand out the workflow tasks now that all settings have been applied
    taskgroups = default_config["workflow"]["taskgroups"]
    default_config["rocoto"]["tasks"] = {}
    for taskgroup in taskgroups:
        tasks = get_yaml_config(homedir / taskgroup)
        keep = {k: v for k, v in tasks.items() if not re.search(r"^default_*", k)}
        default_config["rocoto"]["tasks"].update(keep)


    # Update one more time in case there are user or machine settings to override the tasks
    for cfg in (machine_config, user_config):
        default_config.update_from(cfg)


    # Special logic if EXPT_BASEDIR is a relative path; see config_defaults.yaml for explanation
    expt_basedir = default_config["workflow"]["EXPT_BASEDIR"]
    if not expt_basedir:
        expt_basedir = homedir.parent / "expt_dirs" / expt_basedir
    elif expt_basedir[0] != "/":
        expt_basedir = homedir.parent / "expt_dirs" / expt_basedir
    default_config["workflow"]["EXPT_BASEDIR"] = str(Path(expt_basedir).resolve())

    return default_config


def setup(ushdir, user_config_fn="config.yaml", debug: bool = False):
    # pylint: disable=too-many-statements
    """Validates user-provided configuration settings and derives
    a secondary set of parameters needed to configure a Rocoto-based verification
    workflow. The secondary parameters are derived from a set of required
    parameters defined in ``config_defaults.yaml``, a user-provided
    configuration file (e.g., ``config.yaml``), or a YAML machine file.

    A set of global variable definitions is saved to the experiment
    directory as a bash configure file that is sourced by scripts at run
    time.

    Args:
        ushdir          (str): The full path of the ``ush/`` directory where this script
                               (``setup.py``) is located
        user_config_fn  (str): The name of a user-provided configuration YAML (usually
                               ``config.yaml``)
        debug          (bool): Enable extra output for debugging

    Returns:
        None

    Raises:
        ValueError: If checked configuration values are invalid (e.g., forecast length,
                    ``EXPTDIR`` path)
        FileExistsError: If ``EXPTDIR`` already exists, and ``PREEXISTING_DIR_METHOD`` is not
                         set to a compatible handling method
        FileNotFoundError: If the path to a particular file does not exist or if the file itself
                           does not exist at the expected path
        KeyError: If an invalid value is provided (i.e., for ``GRID_GEN_METHOD``)
    """

    logger = logging.getLogger(__name__)

    # print message
    logger.info(
        f"""
        ========================================================================
        Starting function setup() in \"{os.path.basename(__file__)}\"...
        ========================================================================"""
    )

    # Create a dictionary of config options from defaults, machine, and
    # user config files.
    default_config_fp = os.path.join(ushdir, "config_defaults.yaml")
    user_config_fp = os.path.join(ushdir, user_config_fn)
    expt_config = load_config_for_setup(ushdir, default_config_fp, user_config_fp)

    # Update ush path
    expt_config["user"].update({"USHdir": ushdir,})
    expt_config.dereference(
        context={
            "today": datetime.date.today(),
            "timedelta": datetime.timedelta,
            **expt_config,
            }
        )

    #
    # -----------------------------------------------------------------------
    #
    # Validate the experiment configuration starting with the workflow,
    # then in rough order of the tasks in the workflow
    #
    # -----------------------------------------------------------------------
    #

    # Workflow
    workflow_config = expt_config["workflow"]

    workflow_id = workflow_config["WORKFLOW_ID"]
    logger.info(f"""WORKFLOW ID = {workflow_id}""")

    debug = workflow_config["DEBUG"]
    if debug:
        logger.info(
            """
            Setting VERBOSE to \"True\" because DEBUG has been set to \"True\"..."""
        )
        workflow_config["VERBOSE"] = True

    # The forecast length (in integer hours) cannot contain more than 3 characters.
    # Thus, its maximum value is 999.
    fcst_len_hrs_max = 999
    fcst_len_hrs = workflow_config["FCST_LEN_HRS"]
    if fcst_len_hrs > fcst_len_hrs_max:
        raise ValueError(
            f"""
            Forecast length is greater than maximum allowed length:
              FCST_LEN_HRS = {fcst_len_hrs}
              fcst_len_hrs_max = {fcst_len_hrs_max}"""
        )

    #
    # -----------------------------------------------------------------------
    #
    # Set the full path to the experiment directory.  Then check if it already
    # exists and if so, deal with it as specified by PREEXISTING_DIR_METHOD.
    #
    # -----------------------------------------------------------------------
    #

    # Update some paths that include EXPTDIR and EXPT_BASEDIR
    expt_config.dereference()
    exptdir = workflow_config["EXPTDIR"]
    preexisting_dir_method = workflow_config["PREEXISTING_DIR_METHOD"]
    try:
        check_for_preexist_dir_file(exptdir, preexisting_dir_method)
    except ValueError:
        logger.exception(
            f"""
            Check that the following values are valid:
            EXPTDIR {exptdir}
            PREEXISTING_DIR_METHOD {preexisting_dir_method}
            """
        )
        raise
    except FileExistsError:
        errmsg = dedent(
            f"""
            EXPTDIR ({exptdir}) exists, and PREEXISTING_DIR_METHOD = {preexisting_dir_method}

            To ignore this error, delete the directory, or set
            PREEXISTING_DIR_METHOD = delete, or
            PREEXISTING_DIR_METHOD = rename
            in your config file.
            """
        )
        raise FileExistsError(errmsg) from None

    #
    # -----------------------------------------------------------------------
    #
    # Set cron table entry for relaunching the workflow if
    # USE_CRON_TO_RELAUNCH is set to True.
    #
    # -----------------------------------------------------------------------
    #
    if workflow_config["USE_CRON_TO_RELAUNCH"]:
        intvl_mnts = workflow_config["CRON_RELAUNCH_INTVL_MNTS"]
        launch_script_fn = workflow_config["WFLOW_LAUNCH_SCRIPT_FN"]
        launch_log_fn = workflow_config["WFLOW_LAUNCH_LOG_FN"]
        workflow_config["CRONTAB_LINE"] = (
            f"""*/{intvl_mnts} * * * * cd {exptdir} && """
            f"""./{launch_script_fn} called_from_cron="True" >> ./{launch_log_fn} 2>&1"""
        )
    #
    # -----------------------------------------------------------------------
    #
    # Check user settings against platform settings
    #
    # -----------------------------------------------------------------------
    #

    # Before setting task flags, ensure we don't have any invalid rocoto tasks
    # (e.g. metatasks with no tasks, tasks with no associated commands)
    clean_rocoto_dict(expt_config["rocoto"]["tasks"])

    rocoto_config = expt_config["rocoto"]
    rocoto_tasks = rocoto_config["tasks"]

    # A batch system account is specified
    if expt_config["platform"]["WORKFLOW_MANAGER"] != "":
        if not expt_config["user"]["ACCOUNT"]:
            raise ValueError(
                dedent(
                    f"""
                  ACCOUNT must be specified in config or machine file if using a workflow manager.
                  WORKFLOW_MANAGER = {expt_config["platform"].get("WORKFLOW_MANAGER")}\n"""
                )
            )

    # MET and METPLUS directories must be specified
    if not expt_config["platform"]["MET_INSTALL_DIR"]:
        raise ValueError("MET_INSTALL_DIR must be specified in config or machine file.")
    if not expt_config["platform"]["METPLUS_ROOT"]:
        raise ValueError("METPLUS_ROOT must be specified in config or machine file.")

    def _remove_tag(tasks, tag):
        """Remove the tag for all the tasks in the workflow"""

        if not isinstance(tasks, dict):
            return
        for task, task_settings in tasks.items():
            task_type = task.split("_", maxsplit=1)[0]
            if task_type == "task":
                task_settings.pop(tag, None)
            elif task_type == "metatask":
                _remove_tag(task_settings, tag)

    # Remove all memory tags for platforms that do not support them
    remove_memory = expt_config["platform"]["REMOVE_MEMORY"]
    if remove_memory:
        _remove_tag(rocoto_tasks, "memory")

    # Remove exclusive node usage if not in "platform".yaml
    exclusive = expt_config["platform"].get("EXCLUSIVE")
    if not exclusive:
        _remove_tag(rocoto_tasks, "exclusive")

    for part in ["PARTITION_HPSS", "PARTITION_DEFAULT", "PARTITION_FCST"]:
        partition = expt_config["platform"].get(part)
        if not partition:
            _remove_tag(rocoto_tasks, "partition")

    date_first_cycl = workflow_config["DATE_FIRST_CYCL"]
    date_last_cycl = workflow_config["DATE_LAST_CYCL"]
    incr_cycl_freq = workflow_config["INCR_CYCL_FREQ"]

    date_first_cycl_dt = datetime.datetime.strptime(date_first_cycl, "%Y%m%d%H")
    date_last_cycl_dt = datetime.datetime.strptime(date_last_cycl, "%Y%m%d%H")
    cycl_intvl_dt = datetime.timedelta(hours=incr_cycl_freq)
    fcst_len_dt = datetime.timedelta(hours=fcst_len_hrs)
    #
    # -----------------------------------------------------------------------
    #
    # Set some variables needed for running checks on and creating new
    # (derived) configuration variables for the verification.
    #
    # -----------------------------------------------------------------------
    #
    vx_config = expt_config["verification"]
    vx_fcst_output_intvl_hrs = vx_config["VX_FCST_OUTPUT_INTVL_HRS"]
    vx_fcst_output_intvl_dt = datetime.timedelta(hours=vx_fcst_output_intvl_hrs)

    # Generate a list containing the starting times of the cycles.
    cycle_start_times = set_cycle_dates(
        date_first_cycl_dt, date_last_cycl_dt, cycl_intvl_dt, return_type="datetime"
    )

    # Call function that runs the consistency checks on the vx parameters.
    vx_config, _ = check_temporal_consistency_cumul_fields(
        vx_config, cycle_start_times, fcst_len_dt, vx_fcst_output_intvl_dt
    )

    vx_fcst_output_intvl_hrs = vx_config.get("VX_FCST_OUTPUT_INTVL_HRS")

    # To enable arithmetic with dates and times, convert various time
    # intervals from integer to datetime.timedelta objects.
    fcst_len_dt = datetime.timedelta(hours=fcst_len_hrs)
    vx_fcst_output_intvl_dt = datetime.timedelta(hours=vx_fcst_output_intvl_hrs)
    #
    # -----------------------------------------------------------------------
    #
    # Generate a list of forecast output times and a list of obs days (i.e.
    # days on which observations are needed to perform verification because
    # there is forecast output on those days) over all cycles, both for
    # instantaneous fields (e.g. T2m, REFC, RETOP) and for cumulative ones
    # (e.g. APCP).  Then add these lists to the dictionary containing workflow
    # configuration variables.  These will be needed in generating the ROCOTO
    # XML.
    #
    # -----------------------------------------------------------------------
    #
    (
        fcst_output_times_all_cycles,
        obs_days_all_cycles,
    ) = set_fcst_output_times_and_obs_days_all_cycles(
        cycle_start_times, fcst_len_dt, vx_fcst_output_intvl_dt
    )

    workflow_config["OBS_DAYS_ALL_CYCLES_INST"] = obs_days_all_cycles["inst"]
    workflow_config["OBS_DAYS_ALL_CYCLES_CUMUL"] = obs_days_all_cycles["cumul"]
    #
    # -----------------------------------------------------------------------
    #
    # Generate lists of ROCOTO cycledef strings corresonding to the obs days
    # for instantaneous fields and those for cumulative ones.  Then save the
    # lists of cycledefs in the dictionary containing values needed to
    # construct the ROCOTO XML.
    #
    # -----------------------------------------------------------------------
    #

    cycledefs_obs_days_inst = set_rocoto_cycledefs_for_obs_days(
        obs_days_all_cycles["inst"]
    )
    for spec in cycledefs_obs_days_inst:
        rocoto_config["cycledef"].append({
            "attrs": {"group": "cycledefs_obs_days_inst"},
            "spec": spec,
            })

    cycledefs_obs_days_cumul = set_rocoto_cycledefs_for_obs_days(
        obs_days_all_cycles["cumul"]
    )
    for spec in cycledefs_obs_days_cumul:
        rocoto_config["cycledef"].append({
            "attrs": {"group": "cycledefs_obs_days_cumul"},
            "spec": spec,
            })
    #
    # -----------------------------------------------------------------------
    #
    # Generate dictionary of dictionaries that, for each combination of obs
    # type needed and obs day, contains a string list of the times at which
    # that type of observation is needed on that day.  The elements of each
    # list are formatted as 'YYYYMMDDHH'.  This information is used by the
    # day-based get_obs tasks in the workflow to get obs only at those times
    # at which they are needed (as opposed to for the whole day).
    #
    # -----------------------------------------------------------------------
    #
    obs_retrieve_times_by_day = get_obs_retrieve_times_by_day(
        vx_config,
        cycle_start_times,
        fcst_len_dt,
        fcst_output_times_all_cycles,
        obs_days_all_cycles,
    )

    for obtype, obs_days_dict in obs_retrieve_times_by_day.items():
        for obs_day, obs_retrieve_times in obs_days_dict.items():
            array_name = "_".join(["OBS_RETRIEVE_TIMES", obtype, obs_day])
            vx_config[array_name] = obs_retrieve_times
    expt_config["verification"] = vx_config
    #
    # -----------------------------------------------------------------------
    #
    # Remove all verification (meta)tasks which are not needed for the specified
    # list of verification field groups.
    # Note that if the metatask specification depends on the field group, it
    # does not need to be listed here because those metatasks will be removed
    # later by clean_rocoto_dict()
    #
    # -----------------------------------------------------------------------
    #
    vx_field_groups_all_by_obtype = {}
    vx_metatasks_all_by_obtype = {}

    vx_field_groups_all_by_obtype["CCPA"] = ["APCP"]
    vx_metatasks_all_by_obtype["CCPA"] = [
        "task_get_obs_ccpa",
        "metatask_PcpCombine_APCP_all_accums_obs_CCPA",
        "metatask_PcpCombine_APCP_all_accums_all_mems",
        "metatask_GridStat_APCP_all_accums_all_mems",
        "metatask_GenEnsProd_EnsembleStat_APCP_all_accums",
        "metatask_GridStat_APCP_all_accums_ensmeanprob",
    ]

    vx_field_groups_all_by_obtype["NOHRSC"] = ["ASNOW"]
    vx_metatasks_all_by_obtype["NOHRSC"] = [
        "task_get_obs_nohrsc",
        "metatask_PcpCombine_ASNOW_all_accums_obs_NOHRSC",
        "metatask_PcpCombine_ASNOW_all_accums_all_mems",
        "metatask_GridStat_ASNOW_all_accums_all_mems",
        "metatask_GenEnsProd_EnsembleStat_ASNOW_all_accums",
        "metatask_GridStat_ASNOW_all_accums_ensmeanprob",
    ]

    vx_field_groups_all_by_obtype["MRMS"] = ["REFC", "RETOP"]
    vx_metatasks_all_by_obtype["MRMS"] \
    = ["task_get_obs_mrms",
       "metatask_GridStat_REFC_RETOP_all_mems"]

    vx_field_groups_all_by_obtype["NDAS"] = ["SFC", "UPA"]
    vx_metatasks_all_by_obtype["NDAS"] \
    = ["task_get_obs_ndas",
       "task_run_MET_Pb2nc_obs_NDAS",
       "metatask_PointStat_SFC_UPA_ensmeanprob"]

    vx_field_groups_all_by_obtype["AERONET"] = ["AOD"]
    vx_metatasks_all_by_obtype["AERONET"] \
    = ["task_get_obs_aeronet"]

    vx_field_groups_all_by_obtype["AIRNOW"] = ["PM25", "PM10"]
    vx_metatasks_all_by_obtype["AIRNOW"] \
    = ["task_get_obs_airnow"]

    vx_field_groups_all_by_obtype["GOESAOD"] = ["GOESAOD"]
    vx_metatasks_all_by_obtype["GOESAOD"] \
    = ["task_get_obs_goes_aod"]

    vx_field_groups_all_by_obtype["GOESADP"] = ["GOESADP"]
    vx_metatasks_all_by_obtype["GOESADP"] \
    = ["task_get_obs_goes_adp"]

    # If there are no field groups specified for verification, remove those
    # tasks that are common to all observation types.
    vx_field_groups = vx_config["VX_FIELD_GROUPS"]
    if not vx_field_groups:
        metatask = "metatask_check_post_output_all_mems"
        rocoto_config["tasks"].pop(metatask)

    # If for a given obs type none of its field groups are specified for
    # verification, remove all vx metatasks for that obs type.
    for obtype, vx_tasks in vx_field_groups_all_by_obtype.items():
        vx_field_groups_crnt_obtype = list(set(vx_field_groups) & set(vx_tasks))
        if not vx_field_groups_crnt_obtype:
            for metatask in vx_metatasks_all_by_obtype[obtype]:
                if metatask in rocoto_config["tasks"]:
                    logging.info(
                        dedent(
                            f"""
                        Removing verification (meta)task
                          "{metatask}"
                        from workflow since no field groups from observation type "{obtype}" are
                        specified for verification."""
                        )
                    )
                    rocoto_config["tasks"].pop(metatask)
    #
    # -----------------------------------------------------------------------
    #
    # If there are at least some field groups to verify, then make sure that
    # the base directories in which retrieved obs files will be placed are
    # distinct for the different obs types.
    #
    # -----------------------------------------------------------------------
    #
    if vx_field_groups:
        obtypes_all = ["CCPA", "NOHRSC", "MRMS", "NDAS", "AERONET", "AIRNOW", "GOESAOD"]
        obs_basedir_var_names = [f"{obtype}_OBS_DIR" for obtype in obtypes_all]
        obs_basedirs_dict = {key: vx_config[key] for key in obs_basedir_var_names}
        obs_basedirs_orig = list(obs_basedirs_dict.values())
        obs_basedirs_uniq = list(set(obs_basedirs_orig))
        if len(obs_basedirs_orig) != len(obs_basedirs_uniq):
            obs_locations = "\n".join([f"{v} = {p}" for v, p in obs_basedirs_dict.items()])
            msg = dedent(
                f"""
                The base directories for the obs files must be distinct, but at least two
                are identical:
                {obs_locations}

                Modify these in the configuration file to make them distinct and rerun.
                """
            )
            logging.error(msg)
            raise ValueError(msg)

    #
    # -------------------------------------------------------------------
    #
    # Set dependencies for verification tasks that depend on post output
    #
    # -------------------------------------------------------------------
    #
    run_vx_check = rocoto_config["tasks"].get("metatask_check_post_output_all_mems")
    if run_vx_check:
        run_vx_check["task_check_post_output_mem#mem#"]["dependency"] = {
            "or": {
                "and": {
                  "taskvalid": {"attrs": {"task": "run_fcst__mem#mem#"}},
                  "taskdep": {"attrs": {"task": "run_fcst__mem#mem#"}},
                },
                "not": {
                  "taskvalid": {"attrs": {"task": "run_fcst__mem#mem#"}},
                },
            },
        }

    # remove the data key -- it's not needed beyond this point
    if "data" in expt_config:
        expt_config.pop("data")

    #
    # -----------------------------------------------------------------------
    #
    # Forecast settings
    #
    # -----------------------------------------------------------------------
    #

    workflow_config = expt_config["workflow"]

    # set varying forecast lengths only when fcst_len_hrs=-1
    if fcst_len_hrs == -1:
        fcst_len_cycl = workflow_config.get("FCST_LEN_CYCL")

        # Check that the number of entries divides into a day
        if 24 / incr_cycl_freq != len(fcst_len_cycl):
            # Also allow for the possibility that the user is running
            # cycles for less than a day:
            num_cycles = len(
                set_cycle_dates(date_first_cycl_dt, date_last_cycl_dt, cycl_intvl_dt)
            )

            if num_cycles != len(fcst_len_cycl):
                logger.error(
                    f""" The number of entries in FCST_LEN_CYCL does
              not divide evenly into a 24 hour day or the number of cycles
              in your experiment!
                FCST_LEN_CYCL = {fcst_len_cycl}
              """
                )
                raise ValueError

        # Build cycledef entries for the long forecasts
        # Short forecast cycles will be relevant to all intended
        # forecasts...after all, a 12 hour forecast also encompasses a 3
        # hour forecast, so the short ones will be consistent with the
        # existing default forecast cycledef

        # Reset the hours to the short forecast length
        workflow_config["FCST_LEN_HRS"] = min(fcst_len_cycl)

        # Find the entries that match the long forecast, and map them to
        # their time of day.
        long_fcst_len = max(fcst_len_cycl)
        long_indices = [i for i, x in enumerate(fcst_len_cycl) if x == long_fcst_len]
        long_cycles = [i * incr_cycl_freq for i in long_indices]

        # add one forecast entry per cycle per day
        for hour in long_cycles:
            first = date_first_cycl_dt.replace(hour=hour).strftime("%Y%m%d%H%S")
            last = date_last_cycl_dt.replace(hour=hour).strftime("%Y%m%d%H%S")
            spec = f"{first} {last} 24:00:00"

            rocoto_config["cycledef"].append(
                {"attrs": {"group": "long_forecast"}, "spec": spec}
            )


    # Check to make sure that mandatory forecast variables are set.
    global_sect = expt_config["global"]

    # create experiment dir
    Path(exptdir).mkdir(parents=True)

    #
    # -----------------------------------------------------------------------
    #
    # Check that the set of tasks to run in the workflow is internally
    # consistent.
    #
    # -----------------------------------------------------------------------
    #
    taskgroups = expt_config["workflow"]["taskgroups"]
    ens_vx_tasks = "verify_ens.yaml" in taskgroups
    # Get the value of the configuration flag for ensemble mode (DO_ENSEMBLE)
    # and ensure that it is set to True if ensemble vx tasks are included in
    # the workflow (or vice-versa).
    do_ensemble = global_sect["DO_ENSEMBLE"]
    if (not do_ensemble) and ens_vx_tasks:
        msg = dedent(
            f"""
              Ensemble verification can not be run unless running in ensemble mode:
                  DO_ENSEMBLE = \"{do_ensemble}\"
              Please set DO_ENSEMBLE to True or remove ensemble vx tasks from the
              workflow."""
        )
        raise ValueError(msg)

    #
    # -----------------------------------------------------------------------
    #
    # Generate var_defns.yaml file in the EXPTDIR. This file contains all
    # the user-specified settings from expt_config.
    #
    # -----------------------------------------------------------------------
    #

    logger.debug(str(expt_config))

    global_var_defns_fp = workflow_config["GLOBAL_VAR_DEFNS_FP"]
    # print info message
    logger.info(
        f"""
        Generating the global experiment variable definitions file here:
          GLOBAL_VAR_DEFNS_FP = '{global_var_defns_fp}'
        For more detailed information, set DEBUG to 'True' in the experiment
        configuration file ('{user_config_fn}')."""
    )

    # Final failsafe before writing rocoto yaml to ensure we don't have any invalid dicts
    # (e.g. metatasks with no tasks, tasks with no associated commands)
    clean_rocoto_dict(expt_config["rocoto"]["tasks"])
    expt_config.dereference()

    rocoto_yaml_fp = Path(workflow_config["ROCOTO_YAML_FP"])
    rocoto_yaml = get_yaml_config({"workflow": expt_config["rocoto"]})
    rocoto_yaml.dump(rocoto_yaml_fp)

    var_defns_cfg = get_yaml_config(config=expt_config.data)
    del var_defns_cfg["rocoto"]

    # Fixup a couple of data types:
    var_defns_cfg.dump(Path(global_var_defns_fp))

    # Run render on the Rocoto YAML to check for unrendered values.
    # Quit and report on any found.
    with StringIO() as buffer:
        logger = logging.getLogger()
        handler = logging.StreamHandler(buffer)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        xml_config_str = render(input_file=rocoto_yaml_fp, values_needed=True)
        values_needed = buffer.getvalue().split("\n")[1:]
        logger.removeHandler(handler)
    uwtags = ("!bool", "!float", "!int")
    not_rendered = any(v for v in values_needed if v.strip() != "jobname") or \
            any(tag in xml_config_str for tag in uwtags)
    if not_rendered:
        # Regex to match '{{' or '{%' but not '{{ jobname }}', as the rocoto
        # tool adds jobname for each task. Also matches UW-supported tags.
        pattern = r"({{(?! jobname )|{%.*?%})|!bool|!float|!int"
        line_not_ok = lambda l: any(m for m in re.finditer(pattern, l)) # pylint: disable=unnecessary-lambda-assignment
        unrendered_lines = "\n".join([l.strip() for l in xml_config_str.split("\n") if line_not_ok(l)]) # pylint: disable=line-too-long
        msg = f"""
        Jinja expressions remain in the XML configuration file.

        {str(rocoto_yaml_fp)}

        They include:

        {unrendered_lines}
        """
        raise ValueError(msg)


    #
    # -----------------------------------------------------------------------
    #
    # Check validity of parameters in one place, here in the end.
    #
    # -----------------------------------------------------------------------
    #
    # Validate experiment config against schema
    schema = Path(ushdir) / "experiment.jsonschema"
    valid = validate(schema_file=schema, config_data=var_defns_cfg)

    if not valid:
        logging.error("Experiment configuration is not valid against schema")
        sys.exit(1)


    return expt_config


def clean_rocoto_dict(rocotodict):
    """Removes any invalid entries from ``rocotodict``. Examples of invalid entries are:

    1. A task dictionary containing no "command" key
    2. A metatask definition dependent on a variable with no entries
    3. A metatask dictionary containing no task dictionaries

    Args:
        rocotodict (dict): A dictionary containing Rocoto workflow settings
    """


    # Loop 1: search for tasks with no command key, iterating over metatasks, and popping metatasks
    # with var keys having empty values
    for key in list(rocotodict.keys()):
        if key.split("_", maxsplit=1)[0] == "metatask":
            clean_rocoto_dict(rocotodict[key])
            # After checking for metatasks with no command key, now check for empty var entries
            if rocotodict.get(key).get('var'):
                for varkey in list(rocotodict[key]['var'].keys()):
                    if not rocotodict[key]['var'][varkey]:
                        popped = rocotodict.pop(key)
                        logging.warning(f"Invalid metatask {key} removed due to empty/unset var:")
                        logging.warning(f"{varkey}")
                        logging.debug(f"Removed entry:\n{popped}")
                        break

        elif key.split("_", maxsplit=1)[0] in ["task"]:
            if not rocotodict[key].get("command"):
                popped = rocotodict.pop(key)
                logging.warning(
                    f"Invalid task {key} removed due to empty/unset run command"
                )
                logging.debug(f"Removed entry:\n{popped}")

    # Loop 2: search for metatasks with no tasks in them
    for key in list(rocotodict.keys()):
        if key.split("_", maxsplit=1)[0] == "metatask":
            valid = False
            for key2 in list(rocotodict[key].keys()):
                if key2.split("_", maxsplit=1)[0] == "metatask":
                    clean_rocoto_dict(rocotodict[key][key2])
                    # After above recursion, any nested empty metatasks will have popped themselves
                    if rocotodict[key].get(key2):
                        valid = True
                elif key2.split("_", maxsplit=1)[0] == "task":
                    valid = True
            if not valid:
                popped = rocotodict.pop(key)
                logging.warning(f"Invalid/empty metatask {key} removed")
                logging.debug(f"Removed entry:\n{popped}")


#
# -----------------------------------------------------------------------
#
# Call the function defined above.
#
# -----------------------------------------------------------------------
#
if __name__ == "__main__":
    USHDIR = Path(__file__).resolve().parent.as_posix()
    setup(USHDIR)
