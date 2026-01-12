#!/usr/bin/env python3

"""
User interface to create an experiment directory consistent with the user-defined YAML
configuration file.
"""

# pylint: disable=invalid-name

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path
from stat import S_IXUSR
from string import Template
from textwrap import dedent

from setup import setup
from get_crontab_contents import add_crontab_line
from check_python_version import check_python_version

from uwtools.api import rocoto as uwrocoto


# pylint: disable=too-many-locals,too-many-branches, too-many-statements
def generate_wflow(
    ushdir: str,
    config: str = "config.yaml",
    logfile: str = "log.generate_wflow",
    debug: bool = False,
) -> str:
    """
    Sets up a forecast experiment and creates a workflow (according to the parameters specified
    in the configuration file)

    Args:
        ushdir  (str) : The full path of the ``ush/`` directory where this script is located
        logfile (str) : The name of the file where logging is written
        debug   (bool): Enable extra output for debugging
    Returns:
        EXPTDIR (str) : The full path of the directory where this experiment has been generated
    """

    # Set up logging to write to screen and logfile
    setup_logging(logfile, debug)
    logger = logging.getLogger(__name__)

    # Check python version and presence of some non-standard packages
    check_python_version()

    # Note start of workflow generation
    logger.info(
        """
        ========================================================================
        Starting experiment generation...
        ========================================================================"""
    )

    # The setup function reads the user configuration file and fills in
    # non-user-specified values from config_defaults.yaml
    expt_config = setup(ushdir, user_config_fn=config, debug=debug)

    #
    # -----------------------------------------------------------------------
    #
    # Set the full path to the experiment's rocoto workflow xml file. This
    # file will be placed at the top level of the experiment directory and
    # then used by rocoto to run the workflow.
    #
    # -----------------------------------------------------------------------
    #
    exptdir = expt_config["workflow"]["EXPTDIR"]
    wflow_xml_fn = expt_config["workflow"]["WFLOW_XML_FN"]
    wflow_xml_fp = Path(exptdir, wflow_xml_fn)

    if (wflow_manager := expt_config["platform"]["WORKFLOW_MANAGER"]) == "rocoto":

        logger.info(
            f"""
            Creating rocoto workflow XML file (WFLOW_XML_FP):
              WFLOW_XML_FP = '{wflow_xml_fp}'"""
        )
        rocoto_yaml_fp = expt_config["workflow"]["ROCOTO_YAML_FP"]
        uwrocoto.realize(
            config=rocoto_yaml_fp,
            output_file=wflow_xml_fp,
        )
    #
    # -----------------------------------------------------------------------
    #
    # Create a symlink in the experiment directory that points to the workflow
    # (re)launch script.
    #
    # -----------------------------------------------------------------------
    #
    wflow_launch_script_fp = expt_config["workflow"]["WFLOW_LAUNCH_SCRIPT_FP"]
    wflow_launch_script_fn = expt_config["workflow"]["WFLOW_LAUNCH_SCRIPT_FN"]
    logger.debug(
        f"""
        Creating symlink in the experiment directory (EXPTDIR) that points to the
        workflow launch script (WFLOW_LAUNCH_SCRIPT_FP):
          EXPTDIR = '{exptdir}'
          WFLOW_LAUNCH_SCRIPT_FP = '{wflow_launch_script_fp}'""",
    )

    with open(wflow_launch_script_fp, "r", encoding="utf-8") as launch_script_file:
        launch_script_content = launch_script_file.read()

    # Stage an experiment-specific launch file in the experiment directory
    template = Template(launch_script_content)

    # The script needs several variables from the workflow and user sections
    template_variables = {
        **expt_config["user"],
        **expt_config["workflow"],
    }
    launch_content = template.safe_substitute(template_variables)

    launch_fp = os.path.join(exptdir, wflow_launch_script_fn)
    with open(launch_fp, "w", encoding="utf-8") as expt_launch_fn:
        expt_launch_fn.write(launch_content)

    os.chmod(launch_fp, os.stat(launch_fp).st_mode | S_IXUSR)

    #
    # -----------------------------------------------------------------------
    #
    # If USE_CRON_TO_RELAUNCH is set to True, add a line to the user's
    # cron table to call the (re)launch script every
    # CRON_RELAUNCH_INTVL_MNTS minutes.
    #
    # -----------------------------------------------------------------------
    #
    workflow_config = expt_config["workflow"]
    if workflow_config["USE_CRON_TO_RELAUNCH"]:
        add_crontab_line(
            called_from_cron=False,
            machine=expt_config["user"]["MACHINE"],
            crontab_line=workflow_config["CRONTAB_LINE"],
            exptdir=exptdir,
            debug=debug,
        )

    #
    # -----------------------------------------------------------------------
    #
    # To have a record of how this experiment/workflow was generated, copy
    # the experiment/workflow configuration file to the experiment directo-
    # ry.
    #
    # -----------------------------------------------------------------------
    #
    shutil.copy(os.path.join(ushdir, config), exptdir)

    #
    # -----------------------------------------------------------------------
    #
    # For convenience, print out the commands that need to be issued on the
    # command line in order to launch the workflow and to check its status.
    # Also, print out the line that should be placed in the user's cron table
    # in order for the workflow to be continually resubmitted.
    #
    # -----------------------------------------------------------------------
    #
    if wflow_manager == "rocoto":
        wflow_db_fn = f"{os.path.splitext(wflow_xml_fn)[0]}.db"
        rocotorun_cmd = f"rocotorun -w {wflow_xml_fn} -d {wflow_db_fn} -v 10"
        rocotostat_cmd = f"rocotostat -w {wflow_xml_fn} -d {wflow_db_fn} -v 10"

        cron_relaunch_intvl_mnts = workflow_config["CRON_RELAUNCH_INTVL_MNTS"]
        # pylint: disable=line-too-long
        logger.info(
            f"""
            To launch the workflow, change location to the experiment directory
            (EXPTDIR) and issue the rocotorun command, as follows:

              > cd {exptdir}
              > {rocotorun_cmd}

            To check on the status of the workflow, issue the rocotostat command
            (also from the experiment directory):

              > {rocotostat_cmd}

            Note that:

            1) The rocotorun command must be issued after the completion of each
               task in the workflow in order for the workflow to submit the next
               task(s) to the queue.

            2) In order for the output of the rocotostat command to be up-to-date,
               the rocotorun command must be issued immediately before issuing the
               rocotostat command.

            """
        )
        # pylint: enable=line-too-long

    # If we got to this point everything was successful: move the log
    # file to the experiment directory.
    shutil.move(logfile, exptdir)

    return exptdir


def setup_logging(
    logfile: str = "log.generate_wflow", debug: bool = False
) -> None:
    """
    Sets up logging, printing high-priority (INFO and higher) messages to screen and printing all
    messages with detailed timing and routine info in the specified text file. If ``debug = True``,
    print all messages to both screen and log file.

    Args:
        logfile (str) : The name of the file where logging information is written
        debug   (bool): Enable extra output for debugging
    Returns:
        None

    """
    logging.getLogger().setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(name)-22s %(levelname)-8s %(message)s")

    fh = logging.FileHandler(logfile, mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logging.getLogger().addHandler(fh)
    logging.debug(f"Finished setting up debug file logging in {logfile}")

    # If there are already multiple handlers, that means
    # generate_wflow was called from another function.
    # In that case, do not change the console (print-to-screen) logging.
    if len(logging.getLogger().handlers) > 1:
        return

    console = logging.StreamHandler()
    if debug:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)
    logging.debug("Logging set up successfully")


if __name__ == "__main__":

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Script for setting up a forecast and creating a workflow"
        "according to the parameters specified in the config file\n"
    )

    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Name of experiment config file in YAML format",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Script will be run in debug mode with more verbose output",
    )
    pargs = parser.parse_args()

    USHdir = os.path.dirname(os.path.abspath(__file__))
    wflow_logfile = f"{USHdir}/log.generate_wflow"

    # Call the generate_wflow function defined above to generate the
    # experiment/workflow.
    try:
        expt_dir = generate_wflow(
            USHdir, pargs.config, wflow_logfile, pargs.debug
        )
    except:  # pylint: disable=bare-except
        logging.exception(
            dedent(
                f"""
                *********************************************************************
                FATAL ERROR:
                Experiment generation failed. See the error message(s) printed below.
                For more detailed information, check the log file from the workflow
                generation script: {wflow_logfile}
                *********************************************************************\n
                """
            )
        )
        sys.exit(1)

    # Note workflow generation completion
    logging.info(
        f"""
        ========================================================================

            Experiment generation completed.  The experiment directory is:

              EXPTDIR='{expt_dir}'

        ========================================================================
        """
    )
