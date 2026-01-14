import argparse
import ast
import logging
import math
import os
import subprocess
import sys

from multiprocessing import Pool
from pathlib import Path
from string import Template
from textwrap import dedent

from jinja2 import Environment, FileSystemLoader

import uwtools.api.config as uwconfig

sys.path.insert(1, os.environ['USHdir'])

from set_leadhrs import set_leadhrs
from set_vx_params import set_vx_params

def main(config_file,cdate,obs_dir,field_group,obtype,fcst_level,fcst_thresh):
    """Main program for setting up Point2Grid task and calling METplus wrapper"""
    lgr = logging.getLogger(__name__)

    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    # Set some aliases
    vxcfg = cfg["verification"]

    # Check that basic input directories exist:
    if not Path(obs_dir).is_dir():
        raise FileNotFoundError(f"OBS_DIR does not exist or is not a directory:\n{obs_dir=}")

    # Set paths and file templates for input to and output from the MET/
    # METplus tool to be run as well as other file/directory parameters.

    exptdir=vxcfg["VX_OUTPUT_BASEDIR"]
    MetplusToolName = "Point2Grid"
    if obtype == "GOES":
        obs_in_dir = vxcfg["GOESAOD_OBS_DIR"]
        obs_in_fn_template = vxcfg["OBS_GOESAOD_FN_TEMPLATES"][1]
        adp_input_fn_template = Path(vxcfg["GOESADP_OBS_DIR"],vxcfg["OBS_GOESADP_FN_TEMPLATES"][1])
        output_fn_template = vxcfg["OBS_GOES_AOD_FN_TEMPLATE_POINT2GRID_OUTPUT"]
    else:
        raise ValueError(f"Invalid OBTYPE for {MetplusToolName}: {obtype}")

    #Point2Grid does not honor "time lag" shifts, so remove from template
    fcst_fn_template=Path(
                     vxcfg["VX_FCST_INPUT_BASEDIR"],vxcfg["FCST_SUBDIR_TEMPLATE"],
                     vxcfg["FCST_FN_TEMPLATE"].replace('?shift=-${time_lag}','').replace('?shift=${time_lag}','')
                     )
    output_dir=Path(exptdir, cdate, "metprd", MetplusToolName)
    # Make sure the MET/METplus output directory(ies) exists.
    os.makedirs(output_dir, exist_ok=True)

    # Set the lead hours for which to run the MET/METplus tool.  This is done by starting with the
    # the full list of lead hours for which we expect to find forecast output, then removing any
    # hours for which there is no corresponding observation data.

    # Set the names of the template METplus configuration file, the resulting rendered conf file,
    # and the METplus log file

    metplus_config_tmpl_fn="Point2Grid.conf"
    metplus_config_fn=f"{MetplusToolName}_{field_group}.conf"
    metplus_log_fn=f"metplus.log.{metplus_config_fn}_{cdate}"

    # Load YAML file containing configuration for deterministic verification
    vx_config_dict = uwconfig.get_yaml_config(config=f"{cfg['user']['METPLUS_CONF']}/"\
                                                     f"{vxcfg['VX_CONFIG_DET_FN']}")

    # Define variables that appear in the jinja template, add to existing settings dict.
    settings = {
               'metplus_verbosity_level': vxcfg['METPLUS_VERBOSITY_LEVEL'],
               # Date and forecast hour information.
               'cdate': cdate,
               # Input and output directory/file information.
               'metplus_config_fn': metplus_config_fn,
               'metplus_log_fn': metplus_log_fn,
               'obs_input_dir': obs_in_dir,
               'obs_input_fn_template': obs_in_fn_template,
               'adp_input_fn_template': adp_input_fn_template,
               'output_dir': output_dir,
               'output_fn_template': output_fn_template,
               'fcst_fn_template': fcst_fn_template,
               # Field information.
               'obtype': obtype,
               'metplus_templates_dir': cfg['user']['METPLUS_CONF'],
               'input_field_group': field_group,
               'input_level_fcst': fcst_level,
               'input_thresh_fcst': fcst_thresh,
               # Rest of settings from yaml file
               'vx_config_dict': vx_config_dict
               }

    conf_file = render_metplus_confs(cfg,settings,metplus_config_tmpl_fn)
    lgr.debug(f"{conf_file=}")

    lgr.info(f"Running {MetplusToolName} with METplus")

    run_metplus(os.path.join(cfg['user']['METPLUS_CONF'], "common.conf"),conf_file)

    lgr.info(f"{MetplusToolName} completed successfully.")


def render_metplus_confs(cfg,settings,template_fn):
    """Renders metplus conf files from the appropriate template and user settings."""

    logger = logging.getLogger(__name__)

    logger.debug(f"Loading METplus conf template file: {template_fn}")
    logger.debug(f"from directory {cfg['user']['METPLUS_CONF']}")
    env = Environment(loader=FileSystemLoader(cfg['user']['METPLUS_CONF']))
    template = env.get_template(template_fn)

    #Remove task-specific suffixes if we're only using one task
    settings['metplus_log_fn'] = settings['metplus_log_fn']
    settings['metplus_config_fn'] = settings['metplus_config_fn']
    outconf = f"{settings['output_dir']}/{settings['metplus_config_fn']}"
    logger.debug("Rendering conf file")
    logger.debug(f"metplus log file: {settings['metplus_log_fn']}")
    logger.debug(f"metplus final rendered conf: {settings['metplus_config_fn']}")
    rendered = template.render(settings)
    with open(outconf,'w', encoding="utf-8") as f:
        f.write(rendered)

    return outconf

def run_metplus(common_config,config_fn):
    """Calls the run_metplus script as a subprocess."""
    logger = logging.getLogger(__name__)

    # Run METplus
    metplus_path = os.environ["METPLUS_ROOT"]
    logger.debug(f"{common_config=}")
    logger.debug(f"{config_fn=}")
    logger.debug(f"{metplus_path=}")
    subprocess.run([
        f"{metplus_path}/ush/run_metplus.py",
        "-c", common_config,
        "-c", config_fn
    ], check=True)


def setup_logging(debug=False):

    """Calls initialization functions for logging package, and sets the
    user-defined level for logging in the script."""

    logger = logging.getLogger(__name__)
    if debug:
        print("Setting logging to DEBUG")
        level=logging.DEBUG
    else:
        print("Setting logging to INFO")
        level=logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


if __name__ == "__main__":
    #Parse arguments
    parser = argparse.ArgumentParser(
                     description="exscript for running METplus Point2Grid tasks"\
                     "for deterministic verification\n")

#    parser.add_argument('-c', '--config', default='config.yaml',
#                        help='Name of experiment config file in YAML format')
    parser.add_argument('--config', default='config.yaml',type=str,
                        help='Name of experiment config file in YAML format')
    parser.add_argument('--cycle_date', required=True, type=str,
                        help='Eight-digit cycle date (YYMMDDHH)')
    parser.add_argument('--field_group', required=True, type=str,
                        help='Group of fields for this verification task (e.g. APCP, REFC, SFC, etc.)')
    parser.add_argument('--fcst_level', required=True, type=str,
                        help='The "level" of the observation type as expected by MET (e.g. L0, A03, etc.)')
    parser.add_argument('--fcst_thresh', required=True, type=str,
                        help='The set of forecast thresholds to verify against. Valid options are "all" and "none".')
    parser.add_argument('--obtype', required=True, type=str,
                        help='Observation type for this verification task (e.g. NOHRSC, CCPA, NDAS, etc.)')
    parser.add_argument('--obs_dir', required=True, type=str,
                        help='Observation directory for this obtype')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Script will be run in verbose mode')
    pargs = parser.parse_args()

    setup_logging(debug=pargs.verbose)

    logging.info(dedent(f"""
        ========================================================================
        Executing program: {__file__}

        This is the ex-script for the task that runs the METplus Point2Grid
        tool to perform deterministic verification of the specified field group
        (FIELD_GROUP) for a single forecast.
        ========================================================================"""))

    # Retrieve needed args from environment; should pass these explicitly in the future
    logging.info(f"{os.environ['METPLUS_ROOT']=}")

    main(pargs.config,pargs.cycle_date,pargs.obs_dir,pargs.field_group,pargs.obtype,pargs.fcst_level,pargs.fcst_thresh)
