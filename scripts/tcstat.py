# pylint: disable=logging-fstring-interpolation
"""
This is a python wrapper that sets up and executes the METplus TCSTAT verification task for
verifying cyclone track forecasts.

The script is intended to be called from jobs/TCSTAT.sh.
"""
import argparse
import logging
import os
import subprocess

from multiprocessing import Pool
from pathlib import Path
from string import Template

import uwtools.api.config as uwconfig

from python_utils import eval_metplus_timestr_tmpl, render_metplus_confs, run_metplus, setup_logging

def tcstat(config_file, cdate):
    """
    Set up and execute the METplus TCSTAT verification task for cyclone track statistics.

    This function reads experiment configuration, prepares METplus TCSTAT configuration files
    for each storm ID, and runs the METplus TCSTAT tool to generate track statistics and
    rapid intensification (RI) statistics from TCPAIRS output.

    Args:
        config_file (str): Path to the experiment configuration file in YAML format
        cdate (str): Cycle date in YYYYMMDDHH format

    Returns:
        None
    """
    # pylint: disable=too-many-locals
    lgr = logging.getLogger(__name__)

    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    # Set some aliases
    vxcfg = cfg["verification"]
    tccfg = cfg["tropical"]
    tcstcfg = cfg["tcstat"]

    # Set paths and file templates for input to and output from the MET/
    # METplus tool to be run as well as other file/directory parameters.

    exptdir=vxcfg["VX_OUTPUT_BASEDIR"]
    metplus_tool_camel_case = "TCStat"

    output_dir=Path(exptdir, cdate, "metprd", metplus_tool_camel_case)
    # Make sure the MET/METplus output directory(ies) exists.
    os.makedirs(output_dir, exist_ok=True)


    conf_files=[]
    for storm_id in tccfg['STORM_IDS']:
        # Filenames for TCstat output
        summary_file = tcstcfg["SUMMARY_FILE"]
        # File for Rapid Intensification statistics
        ri_file = tcstcfg["RI_FILE"]
        # Set the names of the template METplus configuration file, the resulting rendered conf file,
        # and the METplus log file
        metplus_config_tmpl_fn="TCSTAT.conf"
        metplus_config_fn=f"{metplus_tool_camel_case}_{storm_id}.conf.0"
        metplus_log_fn=f"metplus.log.{metplus_config_fn[:-7]}_{cdate}.0"
    
        # Load YAML file containing configuration for deterministic verification
        vx_config_dict = uwconfig.get_yaml_config(config=f"{cfg['user']['METPLUS_CONF']}/"\
                                                         f"{vxcfg['VX_CONFIG_DET_FN']}")
    
        # Need to substitute keywords manually since TCSTAT does not accept the "cyclone" keyword
        tcpairs_template = eval_metplus_timestr_tmpl(cfg["tcpairs"]["OUTPUT_TEMPLATE"], cdate, cyclone=storm_id)
        print(f"{tcpairs_template=}")
        tcpairs_output = Path(exptdir, cdate, "metprd", "TCPairs", tcpairs_template + '.tcst')

        # Define variables that appear in the jinja template, add to existing settings dict.
        settings = {
                   'metplus_verbosity_level': vxcfg['METPLUS_VERBOSITY_LEVEL'],
                   # Date and forecast hour information.
                   'cdate': cdate,
                   # Input and output directory/file information. Note that metplus_config_fn,
                   # metplus_log_fn and output_dir are referenced in render_metplus_confs() and so
                   # must always be included in this dictionary
                   'metplus_config_fn': metplus_config_fn,
                   'metplus_log_fn': metplus_log_fn,
                   'tcpairs_output': tcpairs_output,
                   'output_dir': output_dir,
                   'summary_file': summary_file,
                   'ri_file': ri_file,
                   'model': tccfg['MODEL'],
                   # HAFS storm attributes
                   'basin': tccfg['BASIN'],
                   'storm_id': storm_id,
                   }
    
        numprocs=1
        # This function will only output one conf file 
        conf_files.extend(render_metplus_confs(cfg,settings,metplus_config_tmpl_fn,[0],numprocs))
    lgr.debug(f"{conf_files=}")

    lgr.info(f"Running {metplus_tool_camel_case} with METplus with {numprocs} tasks")
    args = []
    for config_fn in conf_files:
        args.append( (os.path.join(cfg['user']['METPLUS_CONF'], "common.conf"),config_fn) )
    # Call run_metplus function for as many processors as specified
        lgr.debug(f"{args=}")
    with Pool(processes=numprocs) as pool:
        pool.starmap(run_metplus,args)

    lgr.info(f"{metplus_tool_camel_case} completed successfully.")


if __name__ == "__main__":
    #Parse arguments
    parser = argparse.ArgumentParser(
                     description="exscript for running METplus TCSTAT task"\
                     "for deterministic verification\n")

    parser.add_argument(
        "--config", default="config.yaml", type=str,
        help="Name of experiment config file in YAML format",
    )
    parser.add_argument(
        "--cycle_date", required=True, type=str,
        help="Eight-digit cycle date (YYMMDDHH)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Script will be run in verbose mode",
    )
    pargs = parser.parse_args()

    setup_logging(debug=pargs.verbose)

    # Retrieve needed args from environment; should pass these explicitly in the future
    logging.info(f"{os.environ['METPLUS_ROOT']=}")

    tcstat(pargs.config,pargs.cycle_date)
