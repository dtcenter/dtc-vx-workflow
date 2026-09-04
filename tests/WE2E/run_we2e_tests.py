#!/usr/bin/env python3
# pylint: disable=logging-fstring-interpolation, too-many-branches, too-many-statements
# pylint: disable=too-many-nested-blocks

"""
Run and monitor WE2E tests.
"""

import argparse
import glob
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent

# add tests/WE2E and ush directories to sys path to find other python files
USH_DIR = Path(__file__).absolute().parents[2] / "ush"
sys.path.insert(0, str(USH_DIR))

from monitor_jobs import monitor_jobs, write_monitor_file
from utils import DEFAULT_DELAY

from uwtools.api.config import get_yaml_config

# pylint: disable=wrong-import-order, wrong-import-position
from generate_wflow import generate_wflow
from python_utils import check_python_version, get_tests_to_run, get_pretty_list

def run_we2e_tests(args) -> None:
    """Runs the Workflow End-to-End (WE2E) tests selected by the user

    Args:
        args    (argparse.Namespace): Command-line arguments

    Returns:
        None
    """

    # Set up logging to write to screen and logfile
    setup_logging(debug=args.debug)
    logging.debug(f"Arguments to run_we2e_tests():\n{args}")

    # Set some variables based on input arguments
    machine = args.machine.lower()

    # Derecho requires long delay between calls to rocotorun due to system-level cacheing of
    # job statuses
    if machine=="derecho" and args.delay < 60:
        logging.info("Derecho requires 60 second delay between calls to rocotorun")
        args.delay=60

    tests_to_run = get_tests_to_run(args.tests)

    pretty_list = get_pretty_list(tests_to_run)
    logging.info(f"Will run {len(tests_to_run)} tests:\n{pretty_list}")

    machine_file = Path(USH_DIR, "machine", f"{machine}.yaml")
    logging.debug(f"Loading machine defaults file {machine_file}")
    machine_defaults = get_yaml_config(machine_file)

    starttime_string = datetime.now().strftime("%Y%m%d%H%M%S")

    monitor_yaml = {}
    for test in tests_to_run:
        # Starting with test yaml template, fill in user-specified and machine- and
        # test-specific options, then write resulting complete config.yaml
        test_name = Path(test).name.split(".")[1]
        logging.debug(f"For test {test_name}, constructing config.yaml")
        test_cfg = get_yaml_config(test)

        test_config_updates = {
            "user": {
                "MACHINE": machine.upper(),
                "ACCOUNT": args.account,
            },
            "workflow": {
                "EXPT_SUBDIR": test_name,
                "USE_CRON_TO_RELAUNCH": args.launch == "cron",
                },
        }

        workflow = test_config_updates["workflow"]
        # Adds an item to the dict only if it has a value
        update = lambda k, v: v and workflow.update({k: v})
        update("CRON_RELAUNCH_INTVL_MNTS", args.cron_relaunch_intvl_mnts)
        update("DEBUG", args.debug_tests)
        update("EXPT_BASEDIR", args.expt_basedir)
        update("EXEC_SUBDIR", args.exec_subdir)
        update("VERBOSE", args.verbose_tests)

        test_cfg.update_from(test_config_updates)
        logging.debug(
            f"Overwriting WE2E-test-specific settings for test \n{test_name}\n"
        )

        # This section checks if we are doing verification on a machine with staged verification
        # obs. If so, and if the config file does not explicitly set the observation locations,
        # fill these in with defaults from the machine files
        obs_vars = [
            "CCPA_OBS_DIR",
            "MRMS_OBS_DIR",
            "NDAS_OBS_DIR",
            "NOHRSC_OBS_DIR",
            'AERONET_OBS_DIR',
            'AIRNOW_OBS_DIR',
        ]
        for obvar in obs_vars:
            mach_path = machine_defaults["platform"].get("TEST_" + obvar)
            if not test_cfg["verification"].get(obvar) and mach_path:
                logging.debug(f"Setting {obvar} = {mach_path} from machine file")
                test_cfg["verification"][obvar] = mach_path

        logging.debug(
            f"Writing updated config.yaml for test {test_name}\n"
            "based on specified command-line arguments:\n"
        )
        logging.debug(str(test_cfg))
        test_cfg.dump(Path(USH_DIR, "config.yaml"))

        logging.info(f"Calling workflow generation function for test {test_name}\n")
        if args.quiet:
            console_handler = logging.getLogger().handlers[1]
            console_handler.setLevel(logging.WARNING)
        expt_dir = generate_wflow(
            ushdir=str(USH_DIR),
            config="config.yaml",
            logfile=f"{str(USH_DIR)}/log.generate_wflow",
            debug=args.debug,
        )
        if args.quiet:
            if args.debug:
                console_handler.setLevel(logging.DEBUG)
            else:
                console_handler.setLevel(logging.INFO)
        logging.info(
            f"Workflow for test {test_name} successfully generated in\n{expt_dir}\n"
        )
        # If this job is not using crontab, we need to add an entry to monitor.yaml
        if "USE_CRON_TO_RELAUNCH" not in test_cfg["workflow"]:
            test_cfg["workflow"].update({"USE_CRON_TO_RELAUNCH": False})
        if not test_cfg["workflow"]["USE_CRON_TO_RELAUNCH"]:
            logging.debug(f"Creating entry for job {test_name} in job monitoring dict")
            workflow_id = f"{test_name}_{starttime_string}"
            monitor_yaml.update({
                workflow_id: {
                    "expt_dir": expt_dir,
                    "status": "CREATED",
                    "start_time": starttime_string,
                    "rocoto_path": machine_defaults["platform"].get("ROCOTO_PATH", ""),
                }
            })
            # Make WORKFLOW_ID actually mean something
            test_cfg["workflow"].update({"WORKFLOW_ID": workflow_id})

    if args.launch == "cron":
        logging.info(
            "All experiments have been generated; using cron to submit workflows"
        )
        logging.info("To view running experiments in cron try `crontab -l`")
        return

    monitor_file = f"WE2E_tests_{starttime_string}.yaml"
    write_monitor_file(monitor_file, monitor_yaml)
    logging.info("All experiments have been generated;")
    logging.info(f"Experiment file {monitor_file} created")

    if args.launch == "none":
        logging.info("To automatically run and monitor experiments, use:\n")
        logging.info(f"./monitor_jobs.py -y={monitor_file}\n")
        return

    write_monitor_file(monitor_file, monitor_yaml)
    logging.debug("calling function that monitors jobs, prints summary")
    try:
        monitor_file = monitor_jobs(
            monitor_yaml,
            monitor_file=monitor_file,
            procs=args.procs,
            debug=args.debug,
            delay=args.delay,
        )
    except KeyboardInterrupt:
        logging.info(
            "\n\nUser interrupted monitor script; to resume monitoring jobs run:\n"
        )
        rerun_string=f"./monitor_jobs.py -y={monitor_file}"
        if args.procs>1:
            rerun_string+=f" -p={args.procs}"
        if args.delay!=DEFAULT_DELAY:
            rerun_string+=f" --delay={args.delay}"

        logging.info(f"{rerun_string}\n")

def setup_logging(logfile: str = "log.run_WE2E_tests", debug: bool = False) -> None:
    """
    Sets up logging, prints high-priority (INFO and higher) messages to screen, and prints all
    messages with detailed timing and routine info to the specified text file.

    Args:
        logfile  (str): Name of the test logging file (default: ``log.run_WE2E_tests``)
        debug   (bool): Set to True for more detailed output/information
    Returns:
        None
    """
    logging.getLogger().setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(name)-16s %(levelname)-8s %(message)s")

    fh = logging.FileHandler(logfile, mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logging.getLogger().addHandler(fh)

    logging.debug(f"Finished setting up debug file logging in {logfile}")
    console = logging.StreamHandler()
    if debug:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)
    logging.debug("Logging set up successfully")


if __name__ == "__main__":

    # Check python version and presence of some non-standard packages
    check_python_version()

    LOGFILE = "log.run_WE2E_tests"

    # Parse arguments
    ap = argparse.ArgumentParser(
        epilog="For more information about config arguments (denoted "
        "in CAPS), see ush/config_defaults.yaml\n",
        add_help=False,
    )
    # Create a group for optional arguments so they can be listed after required args
    required = ap.add_argument_group("required arguments")
    optional = ap.add_argument_group("optional arguments")

    required.add_argument(
        "-m",
        "--machine",
        type=str,
        help="Machine name; see ush/machine/ for valid values",
        required=True,
    )
    required.add_argument(
        "-a",
        "--account",
        type=str,
        help="Account name for running submitted jobs",
        required=True,
    )
    required.add_argument(
        "-t",
        "--tests",
        type=str,
        nargs="*",
        help="""Can be one of three options (in order of priority):
    1. A test name or list of test names.
    2. A subdirectory name under test_configs/
    3. The name of a file (full or relative path) containing a list of test names.
    4. "all" to run all tests
    """,
        required=True,
    )

    optional.add_argument(
        "-h",
        "--help",
        action="help",
        help="Show help and exit",
        )
    optional.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Script will be run in debug mode with more verbose output. "
        + "WARNING: increased verbosity may run very slow on some platforms",
    )
    optional.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress console output from workflow generation; this will help "
        "keep the screen uncluttered",
    )
    optional.add_argument(
        "-p",
        "--procs",
        type=int,
        help="Run resource-heavy tasks (such as calls to rocotorun) in parallel, "
        "with provided number of parallel tasks",
        default=1,
    )
    optional.add_argument(
        "-l",
        "--launch",
        type=str,
        choices=["python", "cron", "none"],
        help="Method for launching jobs. Valid values are:\n"
        " python: [default] Monitor and launch experiments using monitor_jobs.py\n"
        " cron:   Launch expts using ush/launch_vx_wflow.sh from crontab\n"
        " none:   Do not launch experiments; only create experiment directories",
        default="python",
    )

    optional.add_argument(
        "--expt_basedir",
        type=str,
        help="Explicitly set EXPT_BASEDIR for all experiments",
    )
    optional.add_argument(
        "--exec_subdir", type=str, help="Explicitly set EXEC_SUBDIR for all experiments"
    )
    optional.add_argument(
        "--use_cron_to_relaunch",
        action="store_true",
        help='DEPRECATED; DO NOT USE. See "launch" option.',
    )
    optional.add_argument(
        "--cron_relaunch_intvl_mnts",
        type=int,
        help="Overrides CRON_RELAUNCH_INTVL_MNTS for all experiments",
    )
    optional.add_argument(
        "--debug_tests",
        action="store_true",
        help="Explicitly set DEBUG=TRUE for all experiments",
    )
    optional.add_argument(
        "--verbose_tests",
        action="store_true",
        help="Explicitly set VERBOSE=TRUE for all experiments",
    )
    optional.add_argument(
        '--delay', type=int, default=DEFAULT_DELAY,
        help='Pause this number of seconds between calls to rocotorun')

    user_args = ap.parse_args()

    # Exit for deprecated options
    if user_args.use_cron_to_relaunch:
        raise ValueError(
            "\nWARNING: The argument --use_cron_to_relaunch has been superseded by "
            "--launch=cron\nPlease update your workflow accordingly"
        )

    if user_args.procs < 1:
        raise argparse.ArgumentTypeError(
            "You can not have less than one parallel process; select a valid value "
            "for --procs"
        )
    if not user_args.tests:
        raise argparse.ArgumentTypeError("The --tests argument can not be empty")

    # Call main function

    try:
        run_we2e_tests(user_args)
    except: #pylint: disable=bare-except
        logging.exception(
            dedent(
                f"""
                *********************************************************************
                FATAL ERROR:
                Experiment generation failed. See the error message(s) printed below.
                For more detailed information, check the log file from the workflow
                generation script: {LOGFILE}
                *********************************************************************\n
                """
            )
        )
