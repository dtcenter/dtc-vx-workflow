# pylint: disable=logging-fstring-interpolation
"""
Converted from scripts/pcpcombine.sh, this script calls the METplus "PcpCombine" tool to
combine sub-hourly or hourly fields to generate multi-hour accumulations. Input can come
from either observations or a forecast.

The script is intended to be called from jobs/PCPCOMBINE.sh.
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


def pcpcombine(
    config_file: str,
    cdate: str,
    obs_dir: str,
    field_group: str,
    obtype: str,
    accum_hh: int,
    fcst_level: str,
    fcst_thresh: str,
    fcst_or_obs: str,
    ensmem_index: int,
) -> None:
    """Execute a METplus PcpCombine task for obs or forecast accumulation fields.

    Parameters
    ----------
    config_file : str
        Path to the experiment YAML configuration file.
    cdate : str
        Eight-digit cycle date in ``YYYYMMDDHH`` format.
    obs_dir : str
        Directory containing observation files for the chosen obtype.
    field_group : str
        Field group to combine (e.g. APCP, ASNOW, PM25, PM10).
    obtype : str
        Observation type (e.g. CCPA, NOHRSC, AIRNOW).
    accum_hh : int
        Target accumulation period in hours.
    fcst_level : str
        METplus forecast level (e.g. A06).
    fcst_thresh : str
        Forecast threshold set (usually "all" or "none").
    fcst_or_obs : str
        Whether this task processes forecast (``"FCST"``) or observation (``"OBS"``) data.
    ensmem_index : int
        Ensemble member index (0 for deterministic).
    """
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-branches,too-many-statements
    lgr = logging.getLogger(__name__)

    fcst_or_obs = fcst_or_obs.upper()
    if fcst_or_obs not in ("FCST", "OBS"):
        raise ValueError(f"fcst_or_obs must be 'FCST' or 'OBS', got '{fcst_or_obs}'")

    metplus_tool_camel_case = "PcpCombine"

    cfg = uwconfig.get_yaml_config(config=config_file)
    vxcfg = cfg["verification"]
    enscfg = cfg["ensemble"]

    _, obs_fieldname, fcst_fieldname, met_out_name, met_filedir_name = set_vx_params(
        obtype, field_group, accum_hh
    )

    exptdir = vxcfg["VX_OUTPUT_BASEDIR"]
    do_ensemble = enscfg["DO_ENSEMBLE"]
    ensmem = f"mem{str(ensmem_index).zfill(vxcfg['VX_NDIGITS_ENSMEM_NAMES'])}"

    # Make a dictionary of variables that may need to be substituted; these will be used to replace
    # bash-like variables in some strings. This is needed to maintain some functionality while we
    # still have a mix of bash and python exscripts.
    subvars = {
            "FIELD_GROUP": field_group,
            "ACCUM_HH": f"{accum_hh:02}",
            "ensmem_name": f"mem{str(ensmem_index).zfill(vxcfg['VX_NDIGITS_ENSMEM_NAMES'])}",
    }

    pcp_combine_method = "ADD"
    pcp_combine_command = ""

    time_lag = 0
    if fcst_or_obs == "FCST":
        if do_ensemble:
            time_lag = int(enscfg["ENS_TIME_LAG_HRS"][ensmem_index]) * 3600

        subvars["time_lag"]=time_lag
        input_fn_template = Template(
                vxcfg["FCST_FN_TEMPLATE"][ensmem_index]).safe_substitute(subvars)
        input_dir = Path(vxcfg["VX_FCST_INPUT_BASEDIR"])
        output_fn_template = Template(
            vxcfg["FCST_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]
        ).safe_substitute(subvars)

        output_base = Path(exptdir, cdate, ensmem) if do_ensemble else Path(exptdir, cdate)
        output_dir = output_base / "metprd" / f"{metplus_tool_camel_case}_fcst"
        staging_dir = output_base / "stage" / met_filedir_name

        # AIRNOW requires USER_DEFINED combining to build PM2.5/PM10 from model aerosol fields
        if obtype == "AIRNOW":
            pcp_combine_method = "USER_DEFINED"
            smoke_type = vxcfg["FCST_SMOKE_TYPE"]
            if field_group == "PM25":
                if smoke_type == "HRRR":
                    pcp_combine_command = (
                        "-add {FCST_PCP_COMBINE_INPUT_DIR}/{FCST_PCP_COMBINE_INPUT_TEMPLATE}"
                        " -field 'name=\"MASSDEN\"; level=\"Z8\"; convert(x)=x*1e9;'"
                    )
                elif smoke_type == "RRFS":
                    pcp_combine_command = (
                        "-add {FCST_PCP_COMBINE_INPUT_DIR}/{FCST_PCP_COMBINE_INPUT_TEMPLATE}"
                        " 'name=\"MASSDEN\"; level=\"Z8\"; GRIB2_aerosol_type=62010;"
                        " convert(x)=x*1e9;'"
                        " {FCST_PCP_COMBINE_INPUT_DIR}/{FCST_PCP_COMBINE_INPUT_TEMPLATE}"
                        " 'name=\"MASSDEN\"; level=\"Z8\"; GRIB2_aerosol_type=62001;"
                        " GRIB2_aerosol_interval_type=0; convert(x)=x*1e9;'"
                    )
                else:
                    raise ValueError(
                        f"Unsupported FCST_SMOKE_TYPE '{smoke_type}' for PM25"
                    )
            elif field_group == "PM10":
                if smoke_type == "RRFS":
                    pcp_combine_command = (
                        "-add {FCST_PCP_COMBINE_INPUT_DIR}/{FCST_PCP_COMBINE_INPUT_TEMPLATE}"
                        " 'name=\"MASSDEN\"; level=\"Z8\"; GRIB2_aerosol_type=62010;"
                        " convert(x)=x*1e9;'"
                        " {FCST_PCP_COMBINE_INPUT_DIR}/{FCST_PCP_COMBINE_INPUT_TEMPLATE}"
                        " 'name=\"MASSDEN\"; level=\"Z8\"; GRIB2_aerosol_type=62001;"
                        " GRIB2_aerosol_interval_type=0; convert(x)=x*1e9;'"
                        " {FCST_PCP_COMBINE_INPUT_DIR}/{FCST_PCP_COMBINE_INPUT_TEMPLATE}"
                        " 'name=\"MASSDEN\"; level=\"Z8\"; GRIB2_aerosol_type=62001;"
                        " GRIB2_aerosol_interval_type=2; convert(x)=x*1e9;'"
                    )
                else:
                    raise ValueError(
                        f"PM10 only available for RRFS output, not available for {smoke_type}"
                    )

        suffix = f"_{ensmem}"

    else:  # OBS
        subvars["time_lag"]=time_lag
        input_dir = Path(obs_dir)
        input_fn_template = vxcfg[f"OBS_{obtype}_FN_TEMPLATES"][1]
        output_fn_template = Template(
            vxcfg[f"OBS_{obtype}_{field_group}_FN_TEMPLATE_PCPCOMBINE_OUTPUT"]
        ).safe_substitute(subvars)

        output_base = Path(exptdir, cdate, "obs") if do_ensemble else Path(exptdir, cdate)
        output_dir = output_base / "metprd" / f"{metplus_tool_camel_case}_obs"
        staging_dir = output_base / "stage" / met_filedir_name

        suffix = f"_{obtype}"

    os.makedirs(output_dir, exist_ok=True)

    # Sub-interval: model output interval for FCST, obs availability interval for OBS
    if fcst_or_obs == "FCST":
        subintvl = vxcfg["VX_FCST_OUTPUT_INTVL_HRS"]
    else:
        subintvl = vxcfg[f"{obtype}_OBS_AVAIL_INTVL_HRS"]
    input_accum_hh = f"{subintvl:02d}"

    # First pass: get accumulation end hours without file existence check
    lhr_min = 0 if obtype == "AIRNOW" else accum_hh
    vx_leadhr_list = set_leadhrs(
        date_init=cdate,
        lhr_min=lhr_min,
        lhr_max=cfg["workflow"]["FCST_LEN_HRS"],
        lhr_intvl=accum_hh,
        base_dir=input_dir,
        time_lag=time_lag,
        fn_template=str(input_fn_template),
        num_missing_files_max=0,
        skip_check_files=True,
    )

    if not vx_leadhr_list:
        raise RuntimeError(
            f"set_leadhrs returned an empty list for cycle {cdate}, "
            f"{obtype=}, {field_group=}"
        )

    # Second pass: verify sub-interval input files exist for each accumulation window
    for hr_end in vx_leadhr_list:
        hr_start = hr_end - accum_hh + subintvl
        set_leadhrs(
            date_init=cdate,
            lhr_min=hr_start,
            lhr_max=hr_end,
            lhr_intvl=subintvl,
            base_dir=input_dir,
            time_lag=time_lag,
            fn_template=str(input_fn_template),
            num_missing_files_max=0,
        )

    fcst_or_obs_lower = fcst_or_obs.lower()
    metplus_config_tmpl_fn = f"{metplus_tool_camel_case}.conf"
    metplus_config_fn = (
        f"{metplus_tool_camel_case}_{fcst_or_obs_lower}_{met_filedir_name}{suffix}.conf.0"
    )
    metplus_log_fn = (
        f"metplus.log.{metplus_tool_camel_case}_{fcst_or_obs_lower}"
        f"_{met_filedir_name}{suffix}_{cdate}.0"
    )

    settings = {
        "metplus_tool_name": "pcpcombine",
        "MetplusToolName": metplus_tool_camel_case,
        "METPLUS_TOOL_NAME": "PCPCOMBINE",
        "metplus_verbosity_level": vxcfg["METPLUS_VERBOSITY_LEVEL"],
        "cdate": cdate,
        "vx_leadhr_list": ", ".join(map(str, vx_leadhr_list)),
        "metplus_config_fn": metplus_config_fn,
        "metplus_log_fn": metplus_log_fn,
        "input_dir": input_dir,
        "input_fn_template": input_fn_template,
        "output_dir": output_dir,
        "output_fn_template": output_fn_template,
        "staging_dir": staging_dir,
        "vx_fcst_model_name": vxcfg["VX_FCST_MODEL_NAME"],
        "num_ens_members": enscfg["NUM_ENS_MEMBERS"],
        "ensmem_name": ensmem,
        "time_lag": time_lag,
        "fieldname_in_obs_input": obs_fieldname,
        "fieldname_in_fcst_input": fcst_fieldname,
        "fieldname_in_met_output": met_out_name,
        "fieldname_in_met_filedir_names": met_filedir_name,
        "obtype": obtype,
        "FCST_OR_OBS": fcst_or_obs,
        "input_accum_hh": input_accum_hh,
        "output_accum_hh": f"{accum_hh:02}",
        "accum_no_pad": accum_hh,
        "metplus_templates_dir": cfg["user"]["METPLUS_CONF"],
        "input_field_group": field_group,
        "input_level_fcst": fcst_level,
        "input_thresh_fcst": fcst_thresh,
        "pcp_combine_method": pcp_combine_method,
        "pcp_combine_command": pcp_combine_command,
    }

    numprocs = 1
    conf_files = render_metplus_confs(
        cfg, settings, metplus_config_tmpl_fn, vx_leadhr_list, numprocs
    )
    lgr.debug(f"{conf_files=}")

    lgr.info(f"Running {metplus_tool_camel_case} ({fcst_or_obs}) with METplus")
    common_conf = os.path.join(cfg["user"]["METPLUS_CONF"], "common.conf")
    with Pool(processes=numprocs) as pool:
        pool.starmap(run_metplus, [(common_conf, fn) for fn in conf_files])

    lgr.info(f"{metplus_tool_camel_case} completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run METplus PcpCombine for multi-hour accumulation of obs or forecast fields"
    )
    parser.add_argument("--config", default="config.yaml", type=str,
        help="Path to the experiment configuration file in YAML format")
    parser.add_argument("--cycle_date", required=True, type=str,
        help="Eight-digit cycle date (YYYYMMDDHH)")
    parser.add_argument("--obs_dir", required=True, type=str,
        help="Observation directory for this obtype")
    parser.add_argument("--field_group", required=True, type=str,
        help="Field group to combine (e.g. APCP, ASNOW, PM25, PM10)")
    parser.add_argument("--obtype", required=True, type=str,
        help="Observation type (e.g. CCPA, NOHRSC, AIRNOW)")
    parser.add_argument("--accum_hh", required=True, type=int,
        help="Target accumulation period in hours")
    parser.add_argument("--fcst_level", default="", type=str,
        help="METplus forecast level (e.g. A06)")
    parser.add_argument("--fcst_thresh", default="", type=str,
        help="Forecast thresholds to verify against (e.g. all, none)")
    parser.add_argument("--fcst_or_obs", required=True, type=str,
        help="Whether processing forecast (FCST) or observation (OBS) data")
    parser.add_argument("--ensmem_index", type=int, default=0,
        help="Ensemble member index (0 for deterministic)")
    parser.add_argument("-v", "--verbose", action="store_true",
        help="Enable verbose debug output")
    args = parser.parse_args()

    setup_logging(debug=args.verbose)
    logging.debug(f"{os.environ['METPLUS_ROOT']=}")

    pcpcombine(
        args.config, args.cycle_date, args.obs_dir, args.field_group,
        args.obtype, args.accum_hh, args.fcst_level, args.fcst_thresh,
        args.fcst_or_obs, args.ensmem_index,
    )
