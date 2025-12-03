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

def main(config_file,cdate,obs_dir,field_group,obtype,accum_hh,ensmem_index,fcst_level,fcst_thresh):
    """Main program for setting up GridStat task and calling METplus wrapper"""
    lgr = logging.getLogger(__name__)

    # Read config settings
    cfg = uwconfig.get_yaml_config(config=config_file)

    # Set some aliases
    vxcfg = cfg["verification"]
    do_ens = cfg["global"]["DO_ENSEMBLE"]

    # Check that basic input directories exist:
    if not Path(obs_dir).is_dir():
        raise FileNotFoundError(f"OBS_DIR does not exist or is not a directory:\n{obs_dir=}")

    # Set various verification parameters associated with the field to be verified
    geom, _, _, met_out_name, met_filedir_name = set_vx_params(obtype,field_group,accum_hh)

    ensmem=f"mem{str(ensmem_index).zfill(vxcfg['VX_NDIGITS_ENSMEM_NAMES'])}"

    # Set ensemble time lag settings
    lgr.debug(f"{cfg['global']['ENS_TIME_LAG_HRS']=}")
    lgr.debug(f"{ensmem_index=}")
    lgr.debug(f"{vxcfg['VX_NDIGITS_ENSMEM_NAMES']=}")
    time_lag = 0
    if do_ens:
        time_lag_hrs = ast.literal_eval(cfg['global']['ENS_TIME_LAG_HRS'])[ensmem_index-1]
        time_lag = time_lag_hrs*3600

    # Make a dictionary of variables that may need to be substituted; these will be used to replace
    # bash-like variables in some strings. This is needed to maintain some functionality while we
    # still have a mix of bash and python exscripts.
    subvars = {
            "FIELD_GROUP": field_group,
            "ACCUM_HH": f"{accum_hh:02}",
            "ensmem_name": f"mem{str(ensmem_index).zfill(vxcfg['VX_NDIGITS_ENSMEM_NAMES'])}",
            "time_lag": time_lag,
              }

    # Set paths and file templates for input to and output from the MET/
    # METplus tool to be run as well as other file/directory parameters.

    exptdir=vxcfg["VX_OUTPUT_BASEDIR"]
    if geom == "grid":
        metplus_tool_name = "grid_stat"
        MetplusToolName = "GridStat"
        METPLUS_TOOL_NAME = "GRID_STAT"
        if "APCP" in met_filedir_name:
            if do_ens:
                obs_in_dir = Path(exptdir, cdate, "obs", "metprd", "PcpCombine_obs")
                fcst_in_dir = Path(exptdir, cdate, ensmem, "metprd", "PcpCombine_fcst")
            else:
                obs_in_dir = Path(exptdir, cdate, "metprd", "PcpCombine_obs")
                fcst_in_dir = Path(exptdir, cdate, "metprd", "PcpCombine_fcst")
            obs_in_fn_template = Template(vxcfg["OBS_CCPA_APCP_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]).substitute(subvars)
            lgr.debug(f"{vxcfg['FCST_FN_TEMPLATE_PCPCOMBINE_OUTPUT']=}")
            fcst_in_fn_template = Template(vxcfg["FCST_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]).substitute(subvars)
            lgr.debug(f"{fcst_in_fn_template=}")
        elif "ASNOW" in met_filedir_name:
            if do_ens:
                obs_in_dir = Path(exptdir, cdate, "obs", "metprd", "PcpCombine_obs")
                fcst_in_dir = Path(exptdir, cdate, ensmem, "metprd", "PcpCombine_fcst")
            else:
                obs_in_dir = Path(exptdir, cdate, "metprd", "PcpCombine_obs")
                fcst_in_dir = Path(exptdir, cdate, "metprd", "PcpCombine_fcst")
            obs_in_fn_template = Path(Template(vxcfg["OBS_NOHRSC_ASNOW_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]).substitute(subvars))
            fcst_in_fn_template = Path(Template(vxcfg["FCST_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]).substitute(subvars))
        elif met_filedir_name == "REFC":
            obs_in_dir = obs_dir
            fcst_in_dir = vxcfg["VX_FCST_INPUT_BASEDIR"]
            obs_in_fn_template = vxcfg["OBS_MRMS_FN_TEMPLATES"][1]
            fcst_in_fn_template = Path(Template(vxcfg["FCST_SUBDIR_TEMPLATE"]).substitute(subvars),
                                       Template(vxcfg["FCST_FN_TEMPLATE"]).substitute(subvars))
        elif met_filedir_name == "RETOP":
            obs_in_dir = obs_dir
            fcst_in_dir = vxcfg["VX_FCST_INPUT_BASEDIR"]
            obs_in_fn_template = vxcfg["OBS_MRMS_FN_TEMPLATES"][3]
            fcst_in_fn_template = Path(Template(vxcfg["FCST_SUBDIR_TEMPLATE"]).substitute(subvars),
                                       Template(vxcfg["FCST_FN_TEMPLATE"]).substitute(subvars))
        else:
            raise ValueError(f"Invalid OBTYPE for GridStat: {obtype}")

    elif geom == "point":
        metplus_tool_name = "point_stat"
        MetplusToolName = "PointStat"
        METPLUS_TOOL_NAME = "POINT_STAT"
        if obtype == "NDAS":
            obs_in_dir = Path(exptdir, "metprd", "Pb2nc_obs")
            fcst_in_dir = vxcfg["VX_FCST_INPUT_BASEDIR"]
            obs_in_fn_template = vxcfg["OBS_NDAS_SFCandUPA_FN_TEMPLATE_PB2NC_OUTPUT"]
            fcst_in_fn_template = Path(Template(vxcfg["FCST_SUBDIR_TEMPLATE"]).substitute(subvars),
                                       Template(vxcfg["FCST_FN_TEMPLATE"]).substitute(subvars))
        elif obtype == "AERONET":
            #AERONET format has slightly different names for different tasks
            met_filedir_name = "AERONET_AOD"
            obs_in_dir = Path(exptdir, "metprd", "Ascii2nc_obs")
            fcst_in_dir = vxcfg["VX_FCST_INPUT_BASEDIR"]
            obs_in_fn_template = vxcfg["OBS_AERONET_FN_TEMPLATE_ASCII2NC_OUTPUT"]
            fcst_in_fn_template = Path(Template(vxcfg["FCST_SUBDIR_TEMPLATE"]).substitute(subvars),
                                       Template(vxcfg["FCST_FN_TEMPLATE"]).substitute(subvars))
        elif obtype == "AIRNOW":
            # AIRNOW format has slightly different names for different tasks, and also differs
            # based on ob source
            if vxcfg["AIRNOW_INPUT_FORMAT"] == "airnowhourly":
                met_filedir_name = "AIRNOW_HOURLY"
            elif vxcfg["AIRNOW_INPUT_FORMAT"] == "airnowhourlyaqobs":
                met_filedir_name = "AIRNOW_HOURLY_AQOBS"
            else:
                raise ValueError(f"Invalid AIRNOW_INPUT_FORMAT: {vxcfg['AIRNOW_INPUT_FORMAT']}")
            accum_hh=1
            obs_in_dir = Path(exptdir, "metprd", "Ascii2nc_obs")
            if do_ens:
                fcst_in_dir = Path(exptdir, cdate, ensmem, "metprd", "PcpCombine_fcst")
            else:
                fcst_in_dir = Path(exptdir, cdate, "metprd", "PcpCombine_fcst")
            obs_in_fn_template = vxcfg["OBS_AIRNOW_FN_TEMPLATE_ASCII2NC_OUTPUT"]
            fcst_in_fn_template = Path(Template(vxcfg["FCST_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]).substitute(subvars))
        else:
            raise ValueError(f"Invalid OBTYPE for PointStat: {obtype}")
    else:
        raise ValueError(f"Invalid parameters:\n{obtype=}\n{field_group=}\n{accum_hh=}")

    if do_ens:
        output_dir=Path(exptdir, cdate, ensmem, "metprd", MetplusToolName)
        staging_dir=Path(exptdir, cdate, ensmem, "stage", met_filedir_name)
    else:
        output_dir=Path(exptdir, cdate, "metprd", MetplusToolName)
        staging_dir=Path(exptdir, cdate, "stage", met_filedir_name)

    # Make sure the MET/METplus output directory(ies) exists.
    os.makedirs(output_dir, exist_ok=True)

    # Set the lead hours for which to run the MET/METplus tool.  This is done by starting with the
    # the full list of lead hours for which we expect to find forecast output, then removing any
    # hours for which there is no corresponding observation data.

    if obtype in ["CCPA", "NOHRSC"]:
        vx_intvl = vx_hr_start = accum_hh
    else:
        vx_intvl = vxcfg["VX_FCST_OUTPUT_INTVL_HRS"]
        vx_hr_start = 0

    lgr.debug(f"set_leadhrs({cdate},{vx_hr_start},{cfg['workflow']['FCST_LEN_HRS']},{vx_intvl},"\
                 f"{obs_in_dir},{time_lag},{obs_in_fn_template},"\
                 f"{vxcfg['NUM_MISSING_OBS_FILES_MAX']})")
    vx_leadhr_list = set_leadhrs(cdate,vx_hr_start,cfg['workflow']['FCST_LEN_HRS'],vx_intvl,
                                 obs_in_dir,time_lag,str(obs_in_fn_template),
                                 vxcfg['NUM_MISSING_OBS_FILES_MAX'])

    if not vx_leadhr_list:
        raise RuntimeError(f"Call to set_leadhrs({cdate},{vx_hr_start},"\
                           f"{cfg['workflow']['FCST_LEN_HRS']},{vx_intvl},{obs_in_dir},"\
                           f"{time_lag},{obs_in_fn_template},"\
                           f"{vxcfg['NUM_MISSING_OBS_FILES_MAX']})\n"\
                            "returned an empty list.")

    vx_mask_files=[]
    if vxcfg["VX_MASK"]:
        for mask in vxcfg["VX_MASK"]:
            if os.path.isfile(maskfile:=f"{cfg['user']['METPLUS_CONF']}/{mask}.poly"):
                vx_mask_files.append(maskfile)
            else:
                vx_mask_files.append(f"{os.environ['MET_INSTALL_DIR']}/share/met/poly/{mask}.poly")

    # Set the names of the template METplus configuration file, the resulting rendered conf file,
    # and the METplus log file

    metplus_config_tmpl_fn="GridStat_or_PointStat.conf"
    metplus_config_fn=f"{MetplusToolName}_{met_filedir_name}_{field_group}_{ensmem}.conf.0"
    metplus_log_fn=f"metplus.log.{metplus_config_fn[:-7]}_{cdate}.0"

    # Load YAML file containing configuration for deterministic verification
    vx_config_dict = uwconfig.get_yaml_config(config=f"{cfg['user']['METPLUS_CONF']}/"\
                                                     f"{vxcfg['VX_CONFIG_DET_FN']}")

    # Define variables that appear in the jinja template, add to existing settings dict.
    settings = {
               'metplus_tool_name': metplus_tool_name,
               'MetplusToolName': MetplusToolName,
               'METPLUS_TOOL_NAME': METPLUS_TOOL_NAME,
               'metplus_verbosity_level': vxcfg['METPLUS_VERBOSITY_LEVEL'],
               # Date and forecast hour information.
               'cdate': cdate,
               'vx_leadhr_list': ', '.join(map(str,vx_leadhr_list)),
               # Input and output directory/file information.
               'metplus_config_fn': metplus_config_fn,
               'metplus_log_fn': metplus_log_fn,
               'obs_input_dir': obs_in_dir,
               'obs_input_fn_template': obs_in_fn_template,
               'fcst_input_dir': fcst_in_dir,
               'fcst_input_fn_template': fcst_in_fn_template,
               'output_dir': output_dir,
               'staging_dir': staging_dir,
               'vx_fcst_model_name': vxcfg['VX_FCST_MODEL_NAME'],
               # Ensemble and member-specific information.
               'ensmem_name': ensmem,
               'time_lag': time_lag,
               # Field information.
               'fieldname_in_obs_input': obs_in_dir,
               'fieldname_in_fcst_input': fcst_in_dir,
               'fieldname_in_met_output': met_out_name,
               'fieldname_in_met_filedir_names': met_filedir_name,
               'obtype': obtype,
               'accum_hh': f"{accum_hh:02}",
               'accum_no_pad': accum_hh,
               'metplus_templates_dir': cfg['user']['METPLUS_CONF'],
               'input_field_group': field_group,
               'input_level_fcst': fcst_level,
               'input_thresh_fcst': fcst_thresh,
               # Verification mask settings
               'vx_mask': ', '.join(vx_mask_files),
               # Rest of settings from yaml file
               'vx_config_dict': vx_config_dict
               }

    if field_group == "UPA":
        numprocs=math.ceil(vxcfg['VX_TASKS']/2)
    else:
        numprocs=vxcfg['VX_TASKS']

    conf_files = render_metplus_confs(cfg,settings,metplus_config_tmpl_fn,vx_leadhr_list,numprocs)
    lgr.debug(f"{conf_files=}")

    lgr.info(f"Running {MetplusToolName} with METplus with {numprocs} tasks")
    args = []
    for config_fn in conf_files:
        args.append( (os.path.join(cfg['user']['METPLUS_CONF'], "common.conf"),config_fn) )
    # Call run_metplus function for as many processors as specified
        lgr.debug(f"{args=}")
    with Pool(processes=numprocs) as pool:
        pool.starmap(run_metplus,args)

    lgr.info(f"{MetplusToolName} completed successfully.")


def render_metplus_confs(cfg,settings,template_fn,vx_leadhr_list,tasks):
    """Renders metplus conf files from the appropriate template and user settings.
    If VX_TASKS > 1 and vx_leadhr_list > 1, renders a conf file for each parallel task.
    Returns the filename(s) of metplus conf files that were rendered"""

    logger = logging.getLogger(__name__)

    num_fhrs = len(vx_leadhr_list)
    outconfs = []
    logger.debug(f"Loading METplus conf template file: {template_fn}")
    logger.debug(f"from directory {cfg['user']['METPLUS_CONF']}")
    env = Environment(loader=FileSystemLoader(cfg['user']['METPLUS_CONF']))
    template = env.get_template(template_fn)

    if tasks > 1:
        # Break down forecast hours according to number of tasks requested
        if tasks > num_fhrs:
            logger.warning("Number of tasks is greater than number of forecast hours\n"\
                           f"Only running {num_fhrs} tasks in parallel")
            tasks = len(vx_leadhr_list)


        for i in range(tasks):
            logger.debug(f"Rendering conf file for task {i}")
            # We will have i conf files, so append i to the base filename for each
            settings['metplus_log_fn'] = f"{settings['metplus_log_fn'].rsplit('.',1)[0]}.{i}"
            settings['metplus_config_fn'] = f"{settings['metplus_config_fn'].rsplit('.',1)[0]}.{i}"
            outconf = f"{settings['output_dir']}/{settings['metplus_config_fn']}"
            logger.debug(f"metplus log file for task: {settings['metplus_log_fn']}")
            logger.debug(f"metplus final rendered conf for task: {outconf}")
            hours_per_task,remainder = divmod(num_fhrs,tasks)
            # For cases where things don't divide evenly, ensure we get best distribution
            if i >= remainder:
                vx_leadhr_list, task_fhrs = vx_leadhr_list[hours_per_task:],vx_leadhr_list[:hours_per_task]
            else:
                vx_leadhr_list, task_fhrs = vx_leadhr_list[hours_per_task+1:],vx_leadhr_list[:hours_per_task+1]
            settings['vx_leadhr_list'] = ', '.join(map(str,task_fhrs))
            logger.debug(f"Task {i} will process lead hours: {settings['vx_leadhr_list']}")
            rendered = template.render(settings)
            with open(outconf,'w', encoding="utf-8") as f:
                f.write(rendered)
            outconfs.append(outconf)

    else:
        #Remove task-specific suffixes if we're only using one task
        settings['metplus_log_fn'] = settings['metplus_log_fn'].rsplit('.',1)[0]
        settings['metplus_config_fn'] = settings['metplus_config_fn'].rsplit('.',1)[0]
        outconf = f"{settings['output_dir']}/{settings['metplus_config_fn']}"
        logger.debug("Rendering conf file")
        logger.debug(f"metplus log file: {settings['metplus_log_fn']}")
        logger.debug(f"metplus final rendered conf: {settings['metplus_config_fn']}")
        logger.debug(f"Will process lead hours: {settings['vx_leadhr_list']}")
        rendered = template.render(settings)
        with open(outconf,'w', encoding="utf-8") as f:
            f.write(rendered)
        outconfs = [outconf]

    return outconfs

def run_metplus(common_config,config_fn):
    """Calls the run_metplus script as a subprocess. If VX_TASKS > 1 and vx_leadhr_list > 1,
    calls in with starmap for the number of tasks specified."""

    # Run METplus
    metplus_path = os.environ["METPLUS_ROOT"]
    subprocess.run([
        f"{metplus_path}/ush/run_metplus.py",
        "-c", common_config,
        "-c", config_fn
    ], check=True)


def setup_logging(debug=False):

    """Calls initialization functions for logging package, and sets the
    user-defined level for logging in the script."""

    logging.basicConfig()
    logger = logging.getLogger(__name__)
    if debug:
        print("Setting logging to DEBUG")
        logger.setLevel(logging.DEBUG)
    else:
        print("Setting logging to INFO")
        logger.setLevel(logging.INFO)

if __name__ == "__main__":
    #Parse arguments
    parser = argparse.ArgumentParser(
                     description="exscript for running METplus GridStat or PointStat tasks"\
                     "for deterministic verification\n")

#    parser.add_argument('-c', '--config', default='config.yaml',
#                        help='Name of experiment config file in YAML format')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Script will be run in verbose mode')
    pargs = parser.parse_args()

    setup_logging(debug=pargs.verbose)

    logging.info(dedent(f"""
        ========================================================================
        Executing program: {__file__}

        This is the ex-script for the task that runs the METplus GridStat or PointStat
        tool to perform deterministic verification of the specified field group
        (FIELD_GROUP) for a single forecast.
        ========================================================================"""))

    # Retrieve needed args from environment; should pass these explicitly in the future
    config = os.environ['GLOBAL_VAR_DEFNS_FP']
    cycle_date = os.environ['PDY'] + os.environ['cyc']
    field_group = os.environ['FIELD_GROUP']
    obtype = os.environ['OBTYPE']
    obs_dir = os.environ['OBS_DIR']
    if os.environ.get('ACCUM_HH'):
        accum_hh = int(os.environ['ACCUM_HH'])
    else:
        accum_hh = 1
    ensmem_index = int(os.environ['ENSMEM_INDX'])
    fcst_level = os.environ['FCST_LEVEL']
    fcst_thresh = os.environ['FCST_THRESH']

    logging.debug(f"{os.environ['METPLUS_ROOT']=}")

    main(config,cycle_date,obs_dir,field_group,obtype,accum_hh,ensmem_index,fcst_level,fcst_thresh)
