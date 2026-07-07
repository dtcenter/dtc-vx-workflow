# pylint: disable=logging-fstring-interpolation
"""
Converted from scripts/gridstat_or_pointstat_ensprob.sh, this script calls the METplus
"GridStat" or "PointStat" tool to verify ensemble frequency/probability output produced
by GenEnsProd.

The script is intended to be called from jobs/GRIDSTAT_OR_POINTSTAT_ENSPROB.sh.
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


def gridstat_or_pointstat_ensprob(
    config_file: str,
    cdate: str,
    obs_dir: str,
    field_group: str,
    obtype: str,
    accum_hh: int,
    fcst_level: str,
    fcst_thresh: str,
) -> None:
    """Execute a METplus GridStat or PointStat verification task on ensemble probability output.

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
    """
    lgr = logging.getLogger(__name__)

    cfg = uwconfig.get_yaml_config(config=config_file)
    vxcfg = cfg["verification"]

    if not Path(obs_dir).is_dir():
        raise FileNotFoundError(f"{obs_dir=} does not exist or is not a directory")

    geom, _, _, met_out_name, met_filedir_name = set_vx_params(obtype, field_group, accum_hh)

    exptdir = vxcfg["VX_OUTPUT_BASEDIR"]

    # Make a dictionary of variables that may need to be substituted; these will be used to replace
    # bash-like variables in some strings. This is needed to maintain some functionality while we
    # still have a mix of bash and python exscripts.
    subvars = {
            "FIELD_GROUP": field_group,
            "ACCUM_HH": f"{accum_hh:02}",
    }

    if geom == "grid":
        metplus_tool_name = "grid_stat"
        metplus_tool_camel_case = "GridStat"
        if "APCP" in met_filedir_name:
            obs_in_dir = Path(exptdir, cdate, "obs", "metprd", "PcpCombine_obs")
            obs_in_fn_template = Template(
                vxcfg["OBS_CCPA_APCP_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]
            ).substitute(subvars)
        elif "ASNOW" in met_filedir_name:
            obs_in_dir = Path(exptdir, cdate, "obs", "metprd", "PcpCombine_obs")
            obs_in_fn_template = Template(
                vxcfg["OBS_NOHRSC_ASNOW_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]
            ).substitute(subvars)
        elif met_filedir_name == "REFC":
            obs_in_dir = Path(obs_dir)
            obs_in_fn_template = Template(
                vxcfg["OBS_MRMS_FN_TEMPLATES"][1]
            ).substitute(subvars)
        elif met_filedir_name == "RETOP":
            obs_in_dir = Path(obs_dir)
            obs_in_fn_template = Template(
                vxcfg["OBS_MRMS_FN_TEMPLATES"][3]
            ).substitute(subvars)
        else:
            raise ValueError(f"Invalid field group for GridStat ensprob: {field_group}")
        fcst_in_dir = Path(exptdir, cdate, "metprd", "GenEnsProd")

    elif geom == "point":
        metplus_tool_name = "point_stat"
        metplus_tool_camel_case = "PointStat"
        obs_in_dir = Path(exptdir, "metprd", "Pb2nc_obs")
        obs_in_fn_template = Template(
            vxcfg["OBS_NDAS_SFCandUPA_FN_TEMPLATE_PB2NC_OUTPUT"]
        ).substitute(subvars)
        fcst_in_dir = Path(exptdir, cdate, "metprd", "GenEnsProd")

    else:
        raise ValueError(f"Invalid parameters: {obtype=}, {field_group=}, {accum_hh=}")

    fcst_in_fn_template = (
        f"gen_ens_prod_{vxcfg['VX_FCST_MODEL_NAME']}_{met_filedir_name}_{obtype}"
        "_{lead?fmt=%H%M%S}L_{valid?fmt=%Y%m%d}_{valid?fmt=%H%M%S}V.nc"
    )

    output_dir = Path(exptdir, cdate, "metprd", f"{metplus_tool_camel_case}_ensprob")
    staging_dir = Path(exptdir, cdate, "stage", f"{met_filedir_name}_ensprob")
    os.makedirs(output_dir, exist_ok=True)

    if obtype in ("CCPA", "NOHRSC"):
        vx_intvl = vx_hr_start = accum_hh
    else:
        vx_intvl = vxcfg["VX_FCST_OUTPUT_INTVL_HRS"]
        vx_hr_start = 0

    vx_leadhr_list = set_leadhrs(
        date_init=cdate,
        lhr_min=vx_hr_start,
        lhr_max=cfg["workflow"]["FCST_LEN_HRS"],
        lhr_intvl=vx_intvl,
        base_dir=obs_in_dir,
        time_lag=0,
        fn_template=str(obs_in_fn_template),
        num_missing_files_max=vxcfg["NUM_MISSING_OBS_FILES_MAX"],
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

    metplus_config_tmpl_fn = f"{metplus_tool_camel_case}_ensprob.conf"
    metplus_config_fn = (
        f"{metplus_tool_camel_case}_{met_filedir_name}_{cdate}_ensprob.conf.0"
    )
    metplus_log_fn = (
        f"metplus.log.{metplus_tool_camel_case}_{met_filedir_name}_{cdate}_ensprob.0"
    )

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
        "num_ens_members": cfg["ensemble"]["NUM_ENS_MEMBERS"],
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

    numprocs = 1
    conf_files = render_metplus_confs(
        cfg, settings, metplus_config_tmpl_fn, vx_leadhr_list, numprocs
    )
    lgr.debug(f"{conf_files=}")

    lgr.info(f"Running {metplus_tool_camel_case}_ensprob with METplus")
    common_conf = os.path.join(cfg["user"]["METPLUS_CONF"], "common.conf")
    with Pool(processes=numprocs) as pool:
        pool.starmap(run_metplus, [(common_conf, fn) for fn in conf_files])

    lgr.info(f"{metplus_tool_camel_case}_ensprob completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run METplus GridStat or PointStat on ensemble probability output"
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
    parser.add_argument("--fcst_level", required=True, type=str,
        help="METplus forecast level (e.g. L0, A03)")
    parser.add_argument("--fcst_thresh", required=True, type=str,
        help="Forecast thresholds to verify against (e.g. all, none)")
    parser.add_argument("-v", "--verbose", action="store_true",
        help="Enable verbose debug output")
    args = parser.parse_args()

    setup_logging(debug=args.verbose)
    logging.debug(f"{os.environ['METPLUS_ROOT']=}")

    gridstat_or_pointstat_ensprob(
        args.config, args.cycle_date, args.obs_dir, args.field_group,
        args.obtype, args.accum_hh, args.fcst_level, args.fcst_thresh,
    )
