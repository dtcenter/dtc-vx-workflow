#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from python_utils import setup_logging

def eval_metplus_timestr_tmpl(fn_template, init_time, lhr=0, time_lag=0, cyclone=0):
    """
    Calls native METplus routine for evaluating filename templates

    Args:
        fn_template (str): The METplus filename template for finding the files
        init_time   (str): Date string for initial time in YYYYMMDD[mmss] format, where minutes and
                           seconds are optional.
        lhr         (int): [optional] Lead hour (number of hours since init_time)
        time_lag    (int): [optional] Hours of time lag for a time-lagged ensemble member
        cyclone     (int): [optional] The cyclone number for a given tropical cyclone
    Returns:
        str: The fully resolved filename based on the input parameters
    """
    # We import this here to avoid errors for unrelated functions
    try:
        sys.path.append(os.environ['METPLUS_ROOT'])
    except:
        print("\nERROR ERROR ERROR\n")
        print("Environment variable METPLUS_ROOT must be set to use this function\n")
        raise
    from metplus.util import string_template_substitution as sts

    lgr = logging.getLogger(__name__)

    if len(init_time) == 10:
        initdate=datetime.strptime(init_time, '%Y%m%d%H')
    elif len(init_time) == 12:
        initdate=datetime.strptime(init_time, '%Y%m%d%H%M')
    elif len(init_time) == 14:
        initdate=datetime.strptime(init_time, '%Y%m%d%H%M%S')
    else:
        raise ValueError(f"Invalid {init_time=}; must be 10, 12, or 14 characters in length")

    validdate=initdate + timedelta(hours=lhr)
    leadsec=lhr*3600
    # Evaluate the METplus timestring template for the current lead hour
    lgr.debug("Resolving METplus template for:")
    lgr.debug(f"{fn_template=}\ninit={initdate}\nvalid={validdate}\nlead={leadsec}\n{time_lag=}\n{cyclone=}\n")
    # Return the full path with templates resolved
    return sts.do_string_sub(tmpl=fn_template,init=initdate,valid=validdate,
                                   lead=leadsec,time_lag=time_lag,cyclone=str(cyclone))


def eval_metplus_dt_tmpl(fn_template, initdate, validdate=None, time_lag=0, cyclone=0):
    """
    Calls native METplus routine for evaluating filename templates with Datetime objects as input

    Args:
        fn_template (str): The METplus filename template for finding the files
        initdate     (dt): Datetime object of initial time
        validdate    (dt): [optional] Datetime object for valid time
        time_lag    (int): [optional] Hours of time lag for a time-lagged ensemble member
        cyclone     (int): [optional] The cyclone number for a given tropical cyclone
    Returns:
        str: The fully resolved filename based on the input parameters
    """
    # We import this here to avoid errors for unrelated functions
    try:
        sys.path.append(os.environ['METPLUS_ROOT'])
    except:
        print("\nERROR ERROR ERROR\n")
        print("Environment variable METPLUS_ROOT must be set to use this function\n")
        raise
    from metplus.util import string_template_substitution as sts

    lgr = logging.getLogger(__name__)

    if validdate is None:
        validdate=initdate
    lead = validdate - initdate
    leadsec=lead.total_seconds()
    # Evaluate the METplus timestring template for the current lead hour
    lgr.debug("Resolving METplus template for:")
    lgr.debug(f"{fn_template=}\ninit={initdate}\nvalid={validdate}\nlead={leadsec}\n{time_lag=}\n{cyclone=}\n")
    # Return the full path with templates resolved
    return sts.do_string_sub(tmpl=fn_template,init=initdate,valid=validdate,
                                   lead=leadsec,time_lag=time_lag,cyclone=cyclone)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Print a list of forecast hours in bash-readable comma-separated format such that there is a corresponding file (can be observations or forecast files) for each list entry.",
    )
    parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true")
    parser.add_argument("-i", "--init_time", help="Initial date in YYYYMMDDHH[mmss] format", type=str, default='')
    parser.add_argument("-l", "--lhr", help="Lead hour", type=int, required=True)
    parser.add_argument("-tl", "--time_lag", help="Hours of time lag for a time-lagged ensemble member", type=int, default=0)
    parser.add_argument("-ft", "--fn_template", help="Template for file names to search; see ??? for details on template settings", type=str, default='')

    args = parser.parse_args()
    setup_logging(debug=args.verbose)

    filename = eval_metplus_timestr_tmpl(**vars(args))
    # If called from command line, we want to print the resolved filename
    print(filename)
