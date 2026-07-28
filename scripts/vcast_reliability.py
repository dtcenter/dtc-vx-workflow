# pylint: disable=logging-fstring-interpolation
"""
Generate the VCasT (https://github.com/NOAA-GSL/VCasT) configuration YAML files needed to aggregate
ensemble-probability reliability (PCT) statistics and draw reliability diagrams for a single grid
field group, and write an ordered manifest of those YAMLs.

For each grid field group, this writes:
  1. one aggregation YAML (``pct_{group}.yaml``) that aggregates the GridStat_ensprob PCT stats
     across all cycles into a single ``.data`` file, and
  2. one plotting YAML per forecast variable (``plot_{group}_{fcst_var}.yaml``).
It also writes a manifest file listing those YAMLs in the order VCasT must run them (aggregation
first, then the plots that read its output).

This script only GENERATES files; it does NOT run VCasT. It runs in the vx_workflow environment
(which provides uwtools). jobs/VCAST_RELIABILITY.sh then activates the separate ``vcast`` conda
environment (via ``setup_conda.sh vcast``) and runs ``vcast`` on each YAML listed in the manifest,
so this script makes no assumption about the vcast environment being available.

The script is intended to be called from jobs/VCAST_RELIABILITY.sh.
"""

import argparse
import logging
from datetime import datetime, timedelta
from itertools import cycle, islice
from pathlib import Path

import yaml
import uwtools.api.config as uwconfig

from python_utils import setup_logging, merge_field_configs

# Field groups whose ensemble-probability stats are written to GridStat_ensprob. Point-obs groups
# (SFC, UPA -> PointStat_ensprob) are not yet supported and are handled as a separate future case.
GRID_FIELD_GROUPS = ("APCP", "ASNOW", "REFC", "RETOP")

# Cumulative (accumulation) field groups. These are verified one accumulation interval at a time
# (a separate task per accum), so vcast_reliability must be told which accumulation to process via
# accum_hh. Their forecast output steps by the accumulation interval starting at that interval (no
# f00), unlike instantaneous groups (REFC, RETOP) which step by VX_FCST_OUTPUT_INTVL_HRS from f00.
CUMUL_FIELD_GROUPS = ("APCP", "ASNOW")

# Default line-style palettes, cycled to match the number of plotted lead times when the config
# does not specify them explicitly.
_DEFAULT_COLORS = ["blue", "red", "green", "purple", "orange", "brown", "black", "cyan"]
_DEFAULT_MARKERS = ["o", "s", "D", "^", "v", "x", "P", "*"]
_DEFAULT_LINESTYLES = ["-", "--", "-.", ":"]


def _lead_str(hr):
    """MET fcst_lead string for a lead hour: '0' for hour 0, else HHMMSS (e.g. 36 -> '360000')."""
    return "0" if hr == 0 else f"{hr:02d}0000"


def _cycle_to_len(values, n):
    """Return a list of length n formed by cycling through `values`."""
    return list(islice(cycle(values), n))


def _line_styles(taskcfg, n):
    """Return line-style lists of length n. Use the config values when provided (validated to
    match n), otherwise cycle the built-in default palettes to length n."""
    def pick(key, defaults):
        vals = taskcfg.get(key) or []
        if vals:
            if len(vals) != n:
                raise ValueError(
                    f"vcast reliability config '{key}' has {len(vals)} entries but there are {n} "
                    "plotted lead times; line-style lists must have one entry per plotted lead "
                    "(i.e. per PLOT_LEAD_HRS value that is valid for this group/accumulation).")
            return list(vals)
        return _cycle_to_len(defaults, n)

    return {
        "line_color": pick("line_color", _DEFAULT_COLORS),
        "line_marker": pick("line_marker", _DEFAULT_MARKERS),
        "line_type": pick("line_type", _DEFAULT_LINESTYLES),
        "line_width": pick("line_width", [0.8]),
    }


def _write_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def vcast_reliability(config_file, field_group, accum_hh=None, manifest_path=None):
    """Generate the VCasT aggregation + plotting YAMLs for a grid field group, plus a manifest.

    Parameters
    ----------
    config_file : str
        Path to the experiment YAML configuration file.
    field_group : str
        Grid field group to process (one of GRID_FIELD_GROUPS).
    accum_hh : int, optional
        Accumulation interval in hours. Required for cumulative groups (CUMUL_FIELD_GROUPS, e.g.
        APCP/ASNOW), which are processed one accumulation at a time; ignored for instantaneous
        groups (REFC/RETOP).
    manifest_path : str, optional
        Path to write the ordered list of generated YAMLs (one per line, aggregation first). If
        omitted, the manifest is written as ``vcast_run_manifest.txt`` in the working directory.
    """
    lgr = logging.getLogger(__name__)

    if field_group not in GRID_FIELD_GROUPS:
        raise ValueError(
            f"field_group '{field_group}' is not a supported grid field group {GRID_FIELD_GROUPS}. "
            "Point-obs reliability (SFC/UPA via PointStat_ensprob) is not yet implemented.")

    is_cumul = field_group in CUMUL_FIELD_GROUPS
    if is_cumul and accum_hh is None:
        raise ValueError(
            f"field_group '{field_group}' is cumulative; accum_hh is required (one vcast task per "
            "accumulation interval).")

    cfg = uwconfig.get_yaml_config(config=config_file)
    vxcfg = cfg["verification"]
    wfcfg = cfg["workflow"]
    enscfg = cfg["ensemble"]
    taskcfg = cfg["vcast"]["reliability"]

    exptdir = vxcfg["VX_OUTPUT_BASEDIR"]
    model = f"{vxcfg['VX_FCST_MODEL_NAME']}_ensprob"

    # Field entries for this group: shared ensemble fields + per-task overrides, minus exclusions
    # (same field-config resolution the ensprob tasks use).
    vx_config_dict = merge_field_configs(
        enscfg.get("fields") or cfg.get("fields") or {},
        taskcfg.get("fields"),
        exclude=vxcfg.get("VX_FIELDS_EXCLUDE"),
    )
    if field_group not in vx_config_dict or not vx_config_dict[field_group]:
        raise ValueError(f"No field entries defined for field group '{field_group}'")

    # For cumulative groups, select only the entry for the requested accumulation (identified by its
    # fcst_levels, e.g. [A3] for accum_hh=3). Instantaneous groups use all of their entries.
    entries = vx_config_dict[field_group]
    if is_cumul:
        want_level = f"A{accum_hh}"
        entries = [e for e in entries
                   if want_level in [str(lvl) for lvl in e.get("fcst_levels", [])]]
        if not entries:
            raise ValueError(
                f"No '{field_group}' field entry has fcst_levels [{want_level}] "
                f"(accum_hh={accum_hh}); check the fields: config for this group.")

    # Build the ENS_FREQ forecast-variable names so they match the FCST_VAR column of the
    # GridStat_ensprob .stat files: {fcst_name}_ENS_FREQ_{threshold}. fcst_name already carries the
    # accumulation for APCP/ASNOW (e.g. APCP_03). '&&'/'||' are substituted as MET does in names.
    fcst_vars = []
    for entry in entries:
        fcst_name = entry["fcst_name"]
        for thresh in entry.get("fcst_thresholds", []):
            thr = thresh.replace("&&", ".and.").replace("||", ".or.")
            fcst_vars.append(f"{fcst_name}_ENS_FREQ_{thr}")
    if not fcst_vars:
        raise ValueError(f"No fcst_thresholds defined for any selected entry in field group "
                         f"'{field_group}'")

    # Date window: first cycle through (last cycle + forecast length)
    fmt_in, fmt_out = "%Y%m%d%H", "%Y-%m-%d_%H:%M:%S"
    start_dt = datetime.strptime(str(wfcfg["DATE_FIRST_CYCL"]), fmt_in)
    end_dt = (datetime.strptime(str(wfcfg["DATE_LAST_CYCL"]), fmt_in)
              + timedelta(hours=int(wfcfg["FCST_LEN_HRS"])))

    # Forecast lead hours present in the stat files. Cumulative groups step by the accumulation
    # interval starting at that interval (first bucket ends at lead=accum_hh, no f00); instantaneous
    # groups step by the forecast output interval from f00.
    fcst_len = int(wfcfg["FCST_LEN_HRS"])
    intvl = int(vxcfg["VX_FCST_OUTPUT_INTVL_HRS"])
    if is_cumul:
        lead_hrs = list(range(accum_hh, fcst_len + 1, accum_hh))
    else:
        lead_hrs = list(range(0, fcst_len + 1, intvl))
    leads = [_lead_str(h) for h in lead_hrs]

    vx_mask = list(vxcfg.get("VX_MASK") or [])

    # Tag used to prefix output filenames so concurrently-running tasks (e.g. one per APCP
    # accumulation) don't clobber each other. Cumulative groups append the accumulation.
    group_tag = f"{field_group}_{accum_hh:02d}" if is_cumul else field_group

    # Working directory + output filenames, prefixed by group_tag to avoid collisions.
    workdir = Path(exptdir, "metprd", "vcast", field_group)
    workdir.mkdir(parents=True, exist_ok=True)
    agg_file = str(workdir / f"{group_tag}_rel.data")

    # ---- Step 1: aggregation YAML + run ----
    pct_cfg = {
        "input_stat_folder": f"{exptdir}/*/metprd/GridStat_ensprob",
        "line_type": "pct",
        "date_column": "fcst_valid_beg",
        "start_date": start_dt.strftime(fmt_out),
        "end_date": end_dt.strftime(fmt_out),
        "string_filters": {
            "model": [model],
            "fcst_var": fcst_vars,
            "fcst_lead": leads,
            "vx_mask": vx_mask,
        },
        "stat_vars": ["all_thresh"],
        "reformat_file": False,
        "output_reformat_file": str(workdir / f"{group_tag}_filtered.data"),
        "output_file": True,
        "output_plot_file": str(workdir / f"{group_tag}_vars.data"),
        "aggregate": True,
        "group_by": ["model", "fcst_var", "fcst_lead"],
        "output_agg_file": agg_file,
    }
    run_order = []
    pct_yaml = workdir / f"pct_{group_tag}.yaml"
    _write_yaml(pct_yaml, pct_cfg)
    run_order.append(pct_yaml)
    lgr.info(f"Wrote aggregation config {pct_yaml}")

    # ---- Step 2: one plotting YAML + run per forecast variable ----
    # Keep only the requested plot lead hours that actually exist for this group/accumulation;
    # plotting a lead with no data would produce an empty reliability curve.
    valid_leads = set(lead_hrs)
    plot_leads = [int(h) for h in taskcfg["PLOT_LEAD_HRS"] if int(h) in valid_leads]
    dropped = [int(h) for h in taskcfg["PLOT_LEAD_HRS"] if int(h) not in valid_leads]
    if dropped:
        lgr.warning(f"Dropping PLOT_LEAD_HRS {dropped} that are not valid forecast leads for "
                    f"{group_tag} (valid leads: {sorted(valid_leads)})")
    if not plot_leads:
        raise ValueError(f"None of PLOT_LEAD_HRS {list(taskcfg['PLOT_LEAD_HRS'])} are valid "
                         f"forecast leads for {group_tag} (valid leads: {sorted(valid_leads)})")
    styles = _line_styles(taskcfg, len(plot_leads))
    ncols = int(enscfg["NUM_ENS_MEMBERS"])
    mask_label = " ".join(vx_mask)

    for fcst_var in fcst_vars:
        vars_list = [{int(_lead_str(h)): agg_file} for h in plot_leads]
        plot_cfg = {
            "plot_type": "reliability",
            "fcst_var": fcst_var,
            "vars": vars_list,
            "unique": None,
            "plot_title": " ".join(x for x in (model, mask_label, fcst_var, "reliability") if x),
            "legend_title": "Lead Time",
            "labels": [f"{h:02d}" for h in plot_leads],
            "line_color": styles["line_color"],
            "line_marker": styles["line_marker"],
            "line_type": styles["line_type"],
            "line_width": styles["line_width"],
            "ncols": ncols,
            "output_filename": str(workdir / f"{model}_{fcst_var}_reliability.png"),
            "grid": True,
        }
        plot_yaml = workdir / f"plot_{group_tag}_{fcst_var}.yaml"
        _write_yaml(plot_yaml, plot_cfg)
        run_order.append(plot_yaml)
        lgr.info(f"Wrote plot config {plot_yaml}")

    # Write the manifest of YAMLs (absolute paths, in run order) for jobs/VCAST_RELIABILITY.sh to
    # run under the vcast environment.
    manifest = Path(manifest_path) if manifest_path else workdir / "vcast_run_manifest.txt"
    with open(manifest, "w", encoding="utf-8") as f:
        f.writelines(f"{y}\n" for y in run_order)
    lgr.info(f"Wrote VCasT run manifest {manifest} ({len(run_order)} configs)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate the VCasT YAMLs and run manifest needed to aggregate and plot "
                    "ensemble reliability diagrams for a grid field group.")
    parser.add_argument("--config", default="config.yaml", type=str,
                        help="Path to the experiment configuration file in YAML format")
    parser.add_argument("--field_group", required=True, type=str,
                        help=f"Grid field group to plot; one of {GRID_FIELD_GROUPS}")
    parser.add_argument("--accum_hh", default=None, type=int,
                        help=f"Accumulation interval in hours; required for cumulative groups "
                             f"{CUMUL_FIELD_GROUPS}, ignored for instantaneous groups")
    parser.add_argument("--manifest", default=None, type=str,
                        help="Path to write the ordered list of generated VCasT YAMLs (one per "
                             "line, aggregation first) for jobs/VCAST_RELIABILITY.sh to run")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose debug output")
    args = parser.parse_args()

    setup_logging(debug=args.verbose)

    vcast_reliability(args.config, args.field_group, accum_hh=args.accum_hh,
                      manifest_path=args.manifest)
