# pylint: disable=logging-fstring-interpolation
"""
This is a python wrapper that sets up and executes the METplus TCPAIRS verification task for
verifying cyclone track forecasts.

The script is intended to be called from jobs/TCPAIRS.sh.
"""
import argparse
import logging
import os

from multiprocessing import Pool
from pathlib import Path

import uwtools.api.config as uwconfig

from python_utils import eval_metplus_timestr_tmpl, render_metplus_confs, run_metplus, setup_logging
import retrieve_data

def tcpairs(config_file, cdate):
    """
    Set up and execute the METplus TCPAIRS verification task for cyclone track forecasts.

    This function reads experiment configuration, prepares METplus TCPAIRS configuration files
    for each storm ID, and runs the METplus TCPAIRS tool to verify tropical cyclone track forecasts
    against best track observations.

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
    tcpcfg = cfg["tcpairs"]

    # Set paths and file templates for input to and output from the MET/
    # METplus tool to be run as well as other file/directory parameters.

    exptdir=vxcfg["VX_OUTPUT_BASEDIR"]
    metplus_tool_camel_case = "TCPairs"

    output_dir=Path(exptdir, cdate, "metprd", metplus_tool_camel_case)
    # Make sure the MET/METplus output directory(ies) exists.
    os.makedirs(output_dir, exist_ok=True)

    conf_files=[]
    for storm in tccfg['STORM_IDS']:
        storm_id=f"{storm:02}"
        # Ensure best track file is present, and if not, retrieve it:
        best_track_template=tccfg["BEST_TRACK_FILE"]
        # Need to substitute keywords manually to check file existence
        best_track_file = eval_metplus_timestr_tmpl(best_track_template, cdate,
                                                     cyclone=storm_id, basin=tccfg["BASIN"])
        if not os.path.exists(best_track_file):
            lgr.info(f"{best_track_file=} does not exist on disk, attempting to download...")
            dataargs = ['--debug', \
                    '--file_set', 'obs', \
                    '--config', os.path.join(cfg['user']['PARMdir'], 'data_locations.yml'), \
                    '--cycle_date', cdate, \
                    '--cyclone', storm_id, \
                    '--data_stores', "ftp", \
                    '--data_type', "BDECK", \
                    '--output_path', str(output_dir), \
                    '--summary_file', 'retrieve_data.log']
            lgr.debug(f'{dataargs=}')
            retrieve_data.main(dataargs)

        # Set the names of the template METplus configuration file, the resulting rendered conf
        # file, and the METplus log file
        metplus_config_tmpl_fn="TCPAIRS.conf"
        metplus_config_fn=f"{metplus_tool_camel_case}_{storm_id}.conf.0"
        metplus_log_fn=f"metplus.log.{metplus_config_fn[:-7]}_{cdate}.0"

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
                   'fcst_input_dir': tccfg['ADECK_DIR'],
                   'output_dir': output_dir,
                   'output_fn_template': tcpcfg["OUTPUT_TEMPLATE"],
                   'model': tcpcfg['MODEL'],
                   # HAFS storm attributes
                   'basin': tccfg['BASIN'],
                   'storm_id': storm_id,
                   'fcst_track_file': tccfg['ADECK_TEMPLATE'],
                   'best_track_dir': cfg["platform"]["BEST_TRACK_DIR"]
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
    try:
        with Pool(processes=numprocs) as pool:
            pool.starmap(run_metplus,args)
    except Exception:
        lgr.error(
            f"METplus {metplus_tool_camel_case} failed. "
            f"Check the METplus log file(s) for details:"
        )
        raise SystemExit(1) from None

    lgr.info(f"{metplus_tool_camel_case} completed successfully.")


if __name__ == "__main__":
    #Parse arguments
    parser = argparse.ArgumentParser(
                     description="exscript for running METplus TCPAIRS task"\
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

    tcpairs(pargs.config,pargs.cycle_date)
