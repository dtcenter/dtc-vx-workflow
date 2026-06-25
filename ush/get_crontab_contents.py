#!/usr/bin/env python3

import os
import sys
import argparse
import logging
from datetime import datetime
from python_utils import (
    run_command,
    setup_logging,
)


def get_crontab_contents(called_from_cron, machine):
    """
    This function returns the contents of the user's cron table, as well as the command used to
    manipulate the cron table. Typically this latter value will be `crontab`, but on some 
    platforms the version or location of this may change depending on other circumstances.

    Args:
        called_from_cron  (bool): Set this value to ``True`` if script is called from within a 
                                  crontab
        machine           (str) : The name of the current machine
    Returns:
        crontab_cmd       (str) : String containing the "crontab" command for this machine
        crontab_contents  (str) : String containing the contents of the user's cron table.
    """

    logger = logging.getLogger(__name__)

    crontab_cmd = "crontab"

    logger.debug(
        f"""
        Getting crontab content with command:
        =========================================================
          {crontab_cmd} -l
        ========================================================="""
    )

    (_, crontab_contents, _) = run_command(f"{crontab_cmd} -l")

    if crontab_contents.startswith('no crontab for'):
        crontab_contents=''

    logger.debug(
        f"""
        Crontab contents:
        =========================================================
          {crontab_contents}
        ========================================================="""
    )

    # replace single quotes (hopefully in comments) with double quotes
    crontab_contents = crontab_contents.replace("'", '"')

    return crontab_cmd, crontab_contents


def add_crontab_line(called_from_cron, machine, crontab_line, exptdir) -> None:
    """Adds crontab line to cron table

    Args:
        called_from_cron  (bool): Set this value to ``True`` if script is called from within 
                                  a crontab.
        machine           (str) : The name of the current machine
        crontab_line      (str) : Line to be added to cron table
        exptdir           (str) : Path to the experiment directory
    """

    logger = logging.getLogger(__name__)
    #
    # Make a backup copy of the user's crontab file and save it in a file.
    #
    time_stamp = datetime.now().strftime("%F_%T")
    crontab_backup_fp = os.path.join(exptdir, f"crontab.bak.{time_stamp}")
    logger.debug(
        f"""
        Copying contents of user cron table to backup file:
          crontab_backup_fp = '{crontab_backup_fp}'""",
    )

    # Get crontab contents
    crontab_cmd, crontab_contents = get_crontab_contents(called_from_cron, machine)

    # Create backup
    run_command(f"""printf "%s" '{crontab_contents}' > '{crontab_backup_fp}'""")

    # Need to omit commented crontab entries for later logic
    lines = crontab_contents.split('\n')
    cronlines = []
    for line in lines:
        comment = False
        for char in line:
            if char == "#":
                comment = True
                break
            elif char.isspace():
                continue
            else:
                # If we find a character that isn't blank or comment, then this is a normal line
                break
        if not comment:
            cronlines.append(line)
    # Re-join all the separate lines into a multiline string again
    crontab_no_comments = """{}""".format("\n".join(cronlines))
    if crontab_line in crontab_no_comments:
        logger.info(
            f"""
            The following line already exists in the cron table and thus will not be
            added:
              crontab_line = '{crontab_line}'"""
        )
    else:
        logger.debug(
            f"""
            Adding the following line to the user's cron table in order to automatically
            resubmit workflow:
              crontab_line = '{crontab_line}'""",
        )

        # add new line to crontab contents if it doesn't have one
        newline_char = ""
        if crontab_contents and crontab_contents[-1] != "\n":
            newline_char = "\n"

        # add the crontab line
        run_command(
            f"""printf "%s%b%s\n" '{crontab_contents}' '{newline_char}' '{crontab_line}' | {crontab_cmd}"""
        )


def delete_crontab_line(called_from_cron, machine, crontab_line) -> None:
    """Deletes crontab line after job is complete i.e., either SUCCESS/FAILURE
    but not IN PROGRESS status

    Args:
        called_from_cron  (bool): Set this value to ``True`` if script is called from within 
                                  a crontab
        machine           (str) : The name of the current machine
        crontab_line      (str) : Line to be deleted from cron table
    """
    logger = logging.getLogger(__name__)

    #
    # Get the full contents of the user's cron table.
    #
    (crontab_cmd, crontab_contents) = get_crontab_contents(called_from_cron, machine)
    #
    # Remove the line in the contents of the cron table corresponding to the
    # current forecast experiment (if that line is part of the contents).
    # Then record the results back into the user's cron table.
    #
    logger.debug(
        f"""
        Crontab contents before delete:
        =========================================================
          {crontab_contents}
        ========================================================="""
    )

    if crontab_line in crontab_contents:
        #Try removing with a newline first, then fall back to without newline
        crontab_contents = crontab_contents.replace(crontab_line + "\n", "")
        crontab_contents = crontab_contents.replace(crontab_line, "")
    else:
        print(f"\nWARNING: line not found in crontab, nothing to remove:\n{crontab_line}\n")

    run_command(f"""echo '{crontab_contents}' | {crontab_cmd}""")

    logger.debug(
        f"""
        Crontab contents after delete:
        =========================================================
          {crontab_contents}
        ========================================================="""
    )


def _parse_args(argv):
    """Parse command line arguments for deleting crontab line.
    This is needed because it is called from shell script.
    If 'delete' argument is not passed, print the crontab contents
    """
    parser = argparse.ArgumentParser(description="Crontab job manipulation program.")

    parser.add_argument(
        "-c",
        "--called_from_cron",
        action="store_true",
        help="Called from cron.",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Print debug output",
    )

    parser.add_argument(
        "-r",
        "--remove",
        action="store_true",
        help="Remove specified crontab line.",
    )

    parser.add_argument(
        "-l",
        "--line",
        help="Line to remove from crontab. If --remove not specified, has no effect",
    )

    parser.add_argument(
        "-m",
        "--machine",
        help="Machine name",
        required=True
    )

    # Check that inputs are correct and consistent
    args = parser.parse_args(argv)

    if args.remove:
        if args.line is None:
            raise argparse.ArgumentTypeError("--line is a required argument if --remove is specified")

    return args


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    setup_logging(debug=args.debug)
    if args.remove:
        delete_crontab_line(args.called_from_cron,args.machine,args.line)
    else:
        _,out = get_crontab_contents(args.called_from_cron,args.machine)
        print(out)
