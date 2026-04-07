# pylint: disable=logging-fstring-interpolation
"""
This is a python wrapper that sets up and executes the METplus TCRMW verification task for
verifying cyclone track forecasts.

The script is intended to be called from jobs/TCRMW.sh.
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
from set_leadhrs import set_leadhrs

def tcrmw(config_file, cdate):
    """
    Set up and execute the METplus TCRMW verification task for cyclone structural properties.

    This function reads experiment configuration, prepares METplus TCRMW configuration files
    for each storm ID, and runs the METplus TCRMW tool to verify tropical cyclone radius of
    maximum winds (RMW) against forecast data.

    Args:
        config_file (str): Path to the experiment configuration file in YAML format
        cdate (str): Cycle date in YYYYMMDDHH format

    Returns:
        None

    Raises:
        RuntimeError: If the lead hour list is empty or cannot be determined from available forecast files
    """
    # pylint: disable=too-many-locals
    lgr = logging.getLogger(__name__)

    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    # Set some aliases
    vxcfg = cfg["verification"]
    tccfg = cfg["tropical"]
    tcrmwcfg = cfg["tcrmw"]

    # Set paths and file templates for input to and output from the MET/
    # METplus tool to be run as well as other file/directory parameters.

    exptdir=vxcfg["VX_OUTPUT_BASEDIR"]
    metplus_tool_camel_case = "TCRMW"

    output_dir=Path(exptdir, cdate, "metprd", metplus_tool_camel_case)
    # Make sure the MET/METplus output directory(ies) exists.
    os.makedirs(output_dir, exist_ok=True)


    vx_intvl = vxcfg["VX_FCST_OUTPUT_INTVL_HRS"]
    vx_hr_start = 0

    conf_files=[]
    for storm_id in tccfg['STORM_IDS']:
        # Make a dictionary of variables that may need to be substituted; these will be used to replace
        # bash-like variables in some strings. This is needed to maintain some functionality while we
        # still have a mix of bash and python exscripts.
        subvars = {
                "time_lag": 0,
                  }
        fcst_fn_template=os.path.join(Template(vxcfg["FCST_SUBDIR_TEMPLATE"]).substitute(subvars),
                                      Template(vxcfg["FCST_FN_TEMPLATE"]).substitute(subvars))
        lgr.debug(f"{fcst_fn_template=}")

        # TCRMW does not accept "cyclone" keyword
        fcst_fn_template=eval_metplus_timestr_tmpl(fcst_fn_template,cyclone=storm_id)
        adeck_fn_template=eval_metplus_timestr_tmpl(tccfg['ADECK_TEMPLATE'],cyclone=storm_id)
        output_fn_template=eval_metplus_timestr_tmpl(tcrmwcfg["OUTPUT_TEMPLATE"],cyclone=storm_id)
        lgr.debug(f"{fcst_fn_template=}")
        lgr.debug(f"{adeck_fn_template=}")
        lgr.debug(f"{output_fn_template=}")
        # Set the lead hours for which to run the MET/METplus tool.
        lgr.debug(slh_string:=f"set_leadhrs({cdate},{vx_hr_start},{cfg['workflow']['FCST_LEN_HRS']},"\
                     f"{vx_intvl},{vxcfg['VX_FCST_INPUT_BASEDIR']},0,"\
                     f"{fcst_fn_template},{vxcfg['NUM_MISSING_OBS_FILES_MAX']})")
        vx_leadhr_list = set_leadhrs(cdate,vx_hr_start,cfg['workflow']['FCST_LEN_HRS'],vx_intvl,
                                     vxcfg["VX_FCST_INPUT_BASEDIR"],0,str(fcst_fn_template),
                                     vxcfg['NUM_MISSING_OBS_FILES_MAX'],verbose=True)
    
        if not vx_leadhr_list:
            raise RuntimeError(f"Call to {slh_string}\nreturned an empty list.")
        # Set the names of the template METplus configuration file, the resulting rendered conf file,
        # and the METplus log file
        metplus_config_tmpl_fn="TCRMW.conf"
        metplus_config_fn=f"{metplus_tool_camel_case}_{storm_id}.conf.0"
        metplus_log_fn=f"metplus.log.{metplus_config_fn[:-7]}_{cdate}.0"
    
        # Load YAML file containing configuration for deterministic verification
        vx_config_dict = uwconfig.get_yaml_config(config=f"{cfg['user']['METPLUS_CONF']}/"\
                                                         f"{vxcfg['VX_CONFIG_DET_FN']}")
    
#        # Need to substitute keywords manually since TCSTAT does not accept the "cyclone" keyword
#        tcpairs_template = eval_metplus_timestr_tmpl(cfg["tcpairs"]["OUTPUT_TEMPLATE"], cdate, cyclone=storm_id)
#        print(f"{tcpairs_template=}")
#        tcpairs_output = Path(exptdir, cdate, "metprd", "TCPairs", tcpairs_template + '.tcst')

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
                   'fcst_input_dir': vxcfg['VX_FCST_INPUT_BASEDIR'],
                   'fcst_fn_template': fcst_fn_template,
                   'adeck_input_dir': tccfg['ADECK_DIR'],
                   'adeck_track_file': adeck_fn_template,
                   'output_dir': output_dir,
                   'output_fn_template': output_fn_template,
                   'model': tccfg['MODEL'],
                   # HAFS storm attributes
                   'basin': tccfg['BASIN'],
                   'storm_id': storm_id,
                   }
    
        numprocs=1
        # This function will only output one conf file 
        conf_files.extend(render_metplus_confs(cfg,settings,metplus_config_tmpl_fn,vx_leadhr_list,numprocs))
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
                     description="exscript for running METplus TCRMW task"\
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

    tcrmw(pargs.config,pargs.cycle_date)
