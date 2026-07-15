# pylint: disable=logging-fstring-interpolation
"""
Converted from scripts/genensprod_or_ensemblestat.sh, this script calls either the METplus
"GenEnsProd" tool to generate ensemble products or the "EnsembleStat" tool to perform
ensemble-based verification.

The script is intended to be called from jobs/GENENSPROD_OR_ENSEMBLESTAT.sh.
"""

import argparse
import logging
import os

from multiprocessing import Pool
from pathlib import Path
from string import Template

import uwtools.api.config as uwconfig

from python_utils import run_metplus, render_metplus_confs, setup_logging
from set_leadhrs import set_leadhrs
from set_vx_params import set_vx_params

# Maps uppercase Rocoto METPLUSTOOLNAME to (CamelCase, snake_case) tool name variants
_TOOL_NAME_MAP = {
    "GENENSPROD":   ("GenEnsProd",   "gen_ens_prod"),
    "ENSEMBLESTAT": ("EnsembleStat", "ensemble_stat"),
}


def genensprod_or_ensemblestat(
    config_file: str,
    cdate: str,
    obs_dir: str,
    field_group: str,
    obtype: str,
    accum_hh: int,
    fcst_level: str,
    fcst_thresh: str,
    metplus_tool: str,
) -> None:
    """Execute a METplus GenEnsProd or EnsembleStat ensemble verification task.

    Parameters
    ----------
    config_file : str
        Path to the experiment YAML configuration file.
    cdate : str
        Eight-digit cycle date in ``YYYYMMDDHH`` format.
    obs_dir : str
        Directory containing observation files for the chosen obtype.
    field_group : str
        Group of observation fields to verify (e.g. APCP, REFC, SFC).
    obtype : str
        Observation type (e.g. NOHRSC, CCPA, NDAS).
    accum_hh : int
        Accumulation hours for the observation type.
    fcst_level : str
        METplus forecast level (e.g. L0, A03).
    fcst_thresh : str
        Forecast threshold set (usually "all" or "none").
    metplus_tool : str
        METplus tool to run: ``"GENENSPROD"`` or ``"ENSEMBLESTAT"`` (case-insensitive).
    """
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-branches,too-many-statements
    lgr = logging.getLogger(__name__)

    key = metplus_tool.upper()
    if key not in _TOOL_NAME_MAP:
        raise ValueError(
            f"Invalid metplus_tool '{metplus_tool}'. "
            f"Valid options: {list(_TOOL_NAME_MAP.keys())}"
        )
    metplus_tool_camel_case, metplus_tool_name = _TOOL_NAME_MAP[key]

    cfg = uwconfig.get_yaml_config(config=config_file)
    vxcfg = cfg["verification"]
    enscfg = cfg["ensemble"]

    if metplus_tool_name == "ensemble_stat":
        if not Path(obs_dir).is_dir():
            raise FileNotFoundError(f"{obs_dir=} does not exist or is not a directory")

    geom, _, _, met_out_name, met_filedir_name = set_vx_params(obtype, field_group, accum_hh)

    exptdir = vxcfg["VX_OUTPUT_BASEDIR"]

    subvars = {
        "FIELD_GROUP": field_group,
        "ACCUM_HH": f"{accum_hh:02}",
        }

    # Build obs input dir/template and forecast base dir
    if geom == "grid":
        if "APCP" in met_filedir_name:
            obs_in_dir = Path(exptdir, cdate, "obs", "metprd", "PcpCombine_obs")
            obs_in_fn_template = Template(
                vxcfg["OBS_CCPA_APCP_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]
            ).substitute(subvars)
            fcst_in_dir = Path(exptdir)
        elif "ASNOW" in met_filedir_name:
            obs_in_dir = Path(exptdir, cdate, "obs", "metprd", "PcpCombine_obs")
            obs_in_fn_template = Template(
                vxcfg["OBS_NOHRSC_ASNOW_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]
            ).substitute(subvars)
            fcst_in_dir = Path(exptdir)
        elif met_filedir_name == "REFC":
            obs_in_dir = Path(obs_dir)
            obs_in_fn_template = Template(
                vxcfg["OBS_MRMS_FN_TEMPLATES"][1]
            ).substitute(subvars)
            fcst_in_dir = Path(vxcfg["VX_FCST_INPUT_BASEDIR"])
        elif met_filedir_name == "RETOP":
            obs_in_dir = Path(obs_dir)
            obs_in_fn_template = Template(
                vxcfg["OBS_MRMS_FN_TEMPLATES"][3]
            ).substitute(subvars)
            fcst_in_dir = Path(vxcfg["VX_FCST_INPUT_BASEDIR"])
        else:
            raise ValueError(
                f"Invalid field group for {metplus_tool_camel_case}: {field_group}"
            )
    elif geom == "point":
        obs_in_dir = Path(exptdir, "metprd", "Pb2nc_obs")
        obs_in_fn_template = Template(
            vxcfg["OBS_NDAS_SFCandUPA_FN_TEMPLATE_PB2NC_OUTPUT"]
        ).substitute(subvars)
        fcst_in_dir = Path(vxcfg["VX_FCST_INPUT_BASEDIR"])
    else:
        raise ValueError(f"Invalid parameters: {obtype=}, {field_group=}, {accum_hh=}")

    fcst_in_fn_templates = []
    for i in range(enscfg["NUM_ENS_MEMBERS"]):
        # Build per-member forecast filename templates (comma-separated list for METplus)
        ensmem = f"mem{str(i).zfill(vxcfg['VX_NDIGITS_ENSMEM_NAMES'])}"
        subvars = {
            "FIELD_GROUP": field_group,
            "ACCUM_HH": f"{accum_hh:02}",
            "time_lag": int(enscfg["ENS_TIME_LAG_HRS"][i]) * 3600,
            "ensmem_name": ensmem,
        }
        if field_group in ("APCP", "ASNOW"):
            tmpl = str(Path(
                cdate, ensmem, "metprd", "PcpCombine_fcst",
                Template(vxcfg["FCST_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]).safe_substitute(subvars),
            ))
        else:
            tmpl = Template(vxcfg["FCST_FN_TEMPLATE"][i]).safe_substitute(subvars)
        fcst_in_fn_templates.append(tmpl)
    fcst_in_fn_template = ", ".join(fcst_in_fn_templates)

    output_dir = Path(exptdir, cdate, "metprd", metplus_tool_camel_case)
    staging_dir = Path(exptdir, cdate, "stage", met_filedir_name)
    os.makedirs(output_dir, exist_ok=True)

    if obtype in ("CCPA", "NOHRSC"):
        vx_intvl = vx_hr_start = accum_hh
    else:
        vx_intvl = vxcfg["VX_FCST_OUTPUT_INTVL_HRS"]
        vx_hr_start = 0

    # GenEnsProd only needs forecast files; skip obs existence check
    vx_leadhr_list = set_leadhrs(
        date_init=cdate,
        lhr_min=vx_hr_start,
        lhr_max=cfg["workflow"]["FCST_LEN_HRS"],
        lhr_intvl=vx_intvl,
        base_dir=obs_in_dir,
        time_lag=0,
        fn_template=str(obs_in_fn_template),
        num_missing_files_max=vxcfg["NUM_MISSING_OBS_FILES_MAX"],
        skip_check_files=(metplus_tool_camel_case == "GenEnsProd"),
    )

    if not vx_leadhr_list:
        raise RuntimeError(
            f"set_leadhrs returned an empty list for cycle {cdate}, "
            f"{obtype=}, {field_group=}"
        )

    vx_mask_files = []
    if vxcfg["VX_MASK"]:
        for mask in vxcfg["VX_MASK"]:
            if os.path.isfile(maskfile := f"{cfg['user']['METPLUS_CONF']}/{mask}.poly"):
                vx_mask_files.append(maskfile)
            else:
                vx_mask_files.append(
                    f"{os.environ['MET_INSTALL_DIR']}/share/met/poly/{mask}.poly"
                )

    metplus_config_tmpl_fn = f"{metplus_tool_camel_case}.conf"
    metplus_config_fn = f"{metplus_tool_camel_case}_{met_filedir_name}_{cdate}.conf.0"
    metplus_log_fn = f"metplus.log.{metplus_tool_camel_case}_{met_filedir_name}_{cdate}.0"

    vx_config_dict = uwconfig.get_yaml_config(
        config=f"{cfg['user']['METPLUS_CONF']}/{vxcfg['VX_CONFIG_ENS_FN']}"
    )

    settings = {
        "metplus_tool_name": metplus_tool_name,
        "MetplusToolName": metplus_tool_camel_case,
        "METPLUS_TOOL_NAME": metplus_tool_name.upper(),
        "metplus_verbosity_level": vxcfg["METPLUS_VERBOSITY_LEVEL"],
        "cdate": cdate,
        "vx_leadhr_list": ", ".join(map(str, vx_leadhr_list)),
        "metplus_config_fn": metplus_config_fn,
        "metplus_log_fn": metplus_log_fn,
        "obs_input_dir": obs_in_dir,
        "obs_input_fn_template": obs_in_fn_template,
        "fcst_input_dir": fcst_in_dir,
        "fcst_input_fn_template": fcst_in_fn_template,
        "output_dir": output_dir,
        "output_fn_template": "",
        "staging_dir": staging_dir,
        "vx_fcst_model_name": vxcfg["VX_FCST_MODEL_NAME"],
        "num_ens_members": enscfg["NUM_ENS_MEMBERS"],
        "ensmem_name": "",
        "time_lag": 0,
        "fieldname_in_obs_input": str(obs_in_dir),
        "fieldname_in_fcst_input": str(fcst_in_dir),
        "fieldname_in_met_output": met_out_name,
        "fieldname_in_met_filedir_names": met_filedir_name,
        "obtype": obtype,
        "accum_hh": f"{accum_hh:02}",
        "accum_no_pad": accum_hh,
        "metplus_templates_dir": cfg["user"]["METPLUS_CONF"],
        "input_field_group": field_group,
        "input_level_fcst": fcst_level,
        "input_thresh_fcst": fcst_thresh,
        "vx_mask": ", ".join(vx_mask_files),
        "vx_config_dict": vx_config_dict,
    }

    numprocs = int(cfg[metplus_tool_camel_case.lower()]["TASKS"])

    conf_files = render_metplus_confs(cfg,settings,metplus_config_tmpl_fn,vx_leadhr_list,numprocs)
    lgr.debug(f"{conf_files=}")

    lgr.info(f"Running {metplus_tool_camel_case} with METplus with {numprocs} tasks")
    mpargs = []
    for config_fn in conf_files:
        mpargs.append( (os.path.join(cfg['user']['METPLUS_CONF'], "common.conf"),config_fn) )
    # Call run_metplus function for as many processors as specified
        lgr.debug(f"{mpargs=}")
    with Pool(processes=numprocs) as pool:
        pool.starmap(run_metplus,mpargs)

    lgr.info(f"{metplus_tool_camel_case} completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run METplus GenEnsProd or EnsembleStat for ensemble verification"
    )
    parser.add_argument("--config", default="config.yaml", type=str,
        help="Path to the experiment configuration file in YAML format")
    parser.add_argument("--cycle_date", required=True, type=str,
        help="Eight-digit cycle date (YYYYMMDDHH)")
    parser.add_argument("--obs_dir", required=True, type=str,
        help="Observation directory for this obtype")
    parser.add_argument("--field_group", required=True, type=str,
        help="Group of fields for this verification task (e.g. APCP, REFC, SFC)")
    parser.add_argument("--obtype", required=True, type=str,
        help="Observation type (e.g. NOHRSC, CCPA, NDAS)")
    parser.add_argument("--accum_hh", default=1, type=int,
        help="Accumulation hours for this observation type")
    parser.add_argument("--fcst_level", default="", type=str,
        help="METplus forecast level (e.g. L0, A03)")
    parser.add_argument("--fcst_thresh", default="", type=str,
        help="Forecast thresholds to verify against (e.g. all, none)")
    parser.add_argument("--metplus_tool", required=True, type=str,
        help="METplus tool to run: GENENSPROD or ENSEMBLESTAT")
    parser.add_argument("-v", "--verbose", action="store_true",
        help="Enable verbose debug output")
    args = parser.parse_args()

    setup_logging(debug=args.verbose)
    logging.debug(f"{os.environ['METPLUS_ROOT']=}")

    genensprod_or_ensemblestat(
        args.config, args.cycle_date, args.obs_dir, args.field_group,
        args.obtype, args.accum_hh, args.fcst_level, args.fcst_thresh,
        args.metplus_tool,
    )
