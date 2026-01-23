#!/usr/bin/env python3
"""plot_point_stat_mpr_by_valid.py

Plot MET Point-Stat MPR for MULTIPLE model init cycles by VALID time (no aggregation).

Complements:
  - plot_point_stat_mpr_by_lead.py (single init, x = lead)

Behavior:
  - X-axis is FCST_VALID_BEG (valid time)
  - One forecast line per init (staggered with init time)
  - One obs line (continuous), de-duplicated by OBS_VALID_BEG

Example:
  python plot_point_stat_mpr_by_valid.py \
    --base_dir /path/to/output \
    --inits 2024050300 2024050312 2024050400 2024050412 \
    --file_var_token PM10 \
    --fcst_var PM10 \
    --station_id 483550034 \
    --vx_mask FULL
"""

import argparse
from pathlib import Path
from typing import Iterable, List, Union, Optional

import pandas as pd
import matplotlib.pyplot as plt

# ----------------
# Parse MET header
# ----------------

# 24 base columns
BASE_COLS_24 = [
    "VERSION", "MODEL", "DESC",
    "FCST_LEAD", "FCST_VALID_BEG", "FCST_VALID_END",
    "OBS_LEAD", "OBS_VALID_BEG", "OBS_VALID_END",
    "FCST_VAR", "FCST_UNITS", "FCST_LEV",
    "OBS_VAR", "OBS_UNITS", "OBS_LEV",
    "OBTYPE", "VX_MASK",
    "INTERP_MTHD", "INTERP_PNTS",
    "FCST_THRESH", "OBS_THRESH", "COV_THRESH", "ALPHA",
    "LINE_TYPE",
]

# 15 MPR-specific columns
MPR_COLS_15 = [
    "TOTAL", "INDEX",
    "OBS_SID", "OBS_LAT", "OBS_LON", "OBS_LVL", "OBS_ELV",
    "FCST", "OBS",
    "CLIMO", "CLIMO_CDF", "CLIMO_MEAN", "CLIMO_STDEV", "CLIMO_MIN", "CLIMO_MAX",
]


def _parse_met_time(s: str) -> pd.Timestamp:
    """MET timestamps: YYYYMMDD_HHMMSS"""
    return pd.to_datetime(s, format="%Y%m%d_%H%M%S", errors="coerce")


def format_init_time(init_str: str):
    """Convert init like '2024050300' into:
      - title string: '2024-05-03 00Z'
      - filename string: '20240503_00Z'
    """
    dt = pd.to_datetime(init_str, format="%Y%m%d%H")
    title_str = dt.strftime("%Y-%m-%d %HZ")
    fname_str = dt.strftime("%Y%m%d_%HZ")
    return title_str, fname_str


def read_point_stat_mpr(files: Union[str, Path, Iterable[Union[str, Path]]]) -> pd.DataFrame:
    """Read one or many MET Point-Stat .stat files and return ONLY MPR lines as a DataFrame.

    Keeps 24 base columns + 15 MPR columns and adds source_file.
    """
    # Normalize file list
    if isinstance(files, (str, Path)):
        p = Path(files)
        if isinstance(files, str) and any(ch in files for ch in ["*", "?", "["]):
            file_list = sorted(Path().glob(files))
        elif p.is_dir():
            file_list = sorted(p.glob("*.stat"))
        else:
            file_list = [p]
    else:
        file_list = [Path(f) for f in files]

    rows: List[dict] = []

    for fp in file_list:
        if not fp.exists():
            continue
        with fp.open("r", errors="ignore") as f:
            for line in f:
                if not line or line.startswith("#") or line.startswith("VERSION"):
                    continue

                parts = line.split()
                if len(parts) < len(BASE_COLS_24):
                    continue

                if parts[len(BASE_COLS_24) - 1] != "MPR":
                    continue

                if len(parts) < len(BASE_COLS_24) + len(MPR_COLS_15):
                    continue

                base = dict(zip(BASE_COLS_24, parts[: len(BASE_COLS_24)]))
                extra = dict(zip(MPR_COLS_15, parts[len(BASE_COLS_24): len(BASE_COLS_24) + len(MPR_COLS_15)]))

                rows.append({**base, **extra, "source_file": str(fp)})

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Numeric columns used in plotting
    for c in ["FCST", "OBS", "OBS_LAT", "OBS_LON", "OBS_LVL", "OBS_ELV"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].replace("NA", pd.NA), errors="coerce")

    # Parse times
    for c in ["FCST_VALID_BEG", "FCST_VALID_END", "OBS_VALID_BEG", "OBS_VALID_END"]:
        if c in df.columns:
            df[c] = df[c].apply(_parse_met_time)

    return df


# ----------------
# File collection
# ----------------

def collect_files_for_init(
    base_dir: Union[str, Path],
    init: str,                   # e.g., "2024050300"
    file_var_token: str,         # token in filename: "AOD", "PM10", "PM25"
) -> List[Path]:
    """Collect Point-Stat .stat files in base_dir/init/ matching a token."""
    init_dir = Path(base_dir) / init
    if not init_dir.is_dir():
        raise FileNotFoundError(f"Init directory not found: {init_dir}")

    glob_pat = f"*_{file_var_token}_??????L_*V.stat"
    return sorted(init_dir.glob(glob_pat))


def collect_files_for_inits(
    base_dir: Union[str, Path],
    inits: List[str],
    file_var_token: str,
) -> List[Path]:
    files: List[Path] = []
    for init in inits:
        files.extend(collect_files_for_init(base_dir, init, file_var_token))
    # Remove dupes while preserving order
    seen = set()
    out: List[Path] = []
    for f in files:
        s = str(f)
        if s not in seen:
            seen.add(s)
            out.append(f)
    return out


def add_init_from_path(df: pd.DataFrame) -> pd.DataFrame:
    """Add an 'init' column derived from parent directory name of source_file.

    Assumes: .../<base_dir>/<init>/<statfile> --> need to fix to be more flexible (after AMS)
    """
    if df.empty:
        return df
    out = df.copy()
    out["init"] = out["source_file"].apply(lambda s: Path(s).parent.name)
    return out


# ----------------------------
# Filter + prepare for plotting
# ----------------------------

def build_station_valid_series_multi(
    mpr_df: pd.DataFrame,
    station_id: str,
    fcst_var: str,
    vx_mask: str = "FULL",
) -> pd.DataFrame:
    """Filter to one station/variable/mask across multiple inits.

    Returns rows sorted by init then FCST_VALID_BEG.
    Keeps one row per (init, FCST_VALID_BEG) if duplicates exist.
    """
    if mpr_df.empty:
        return mpr_df

    df = mpr_df.copy()
    df = df[df["VX_MASK"].astype(str) == str(vx_mask)]
    df = df[df["FCST_VAR"].astype(str) == str(fcst_var)]
    df = df[df["OBS_SID"].astype(str) == str(station_id)]

    if df.empty:
        return df

    if "init" not in df.columns:
        df = add_init_from_path(df)

    # Sort and remove dupes within init/valid
    df = df.sort_values(["init", "FCST_VALID_BEG"]).drop_duplicates(
        subset=["init", "FCST_VALID_BEG"], keep="first"
    )

    return df.reset_index(drop=True)


def build_obs_series(df: pd.DataFrame) -> pd.DataFrame:
    """Build a single obs time series (dedupe by OBS_VALID_BEG)."""
    if df.empty:
        return df

    obs = (
        df[["OBS_VALID_BEG", "OBS"]]
        .dropna(subset=["OBS_VALID_BEG", "OBS"])
        .sort_values("OBS_VALID_BEG")
        .drop_duplicates(subset=["OBS_VALID_BEG"], keep="first")
        .reset_index(drop=True)
    )
    return obs


# -------
# Plot
# -------

def plot_fcst_obs_by_valid(
    df: pd.DataFrame,
    title: Optional[str] = None,
    outfile: Optional[Union[str, Path]] = None,
):
    if df.empty:
        raise ValueError("No matching records after filtering (station/var/vx_mask).")

    fig, ax = plt.subplots(figsize=(12, 5))

    # Obs (continuous)
    obs = build_obs_series(df)
    if not obs.empty:
        ax.plot(obs["OBS_VALID_BEG"], obs["OBS"], marker=".", linewidth=2, label="Obs")

    # Forecast lines (one per init)
    for init, g in df.groupby("init"):
        g = g.dropna(subset=["FCST_VALID_BEG", "FCST"]).sort_values("FCST_VALID_BEG")
        if g.empty:
            continue
        ax.plot(g["FCST_VALID_BEG"], g["FCST"], marker=".", linewidth=1.5, label=f"Fcst {init}")

    var = df["FCST_VAR"].iloc[0] if "FCST_VAR" in df.columns else ""
    units = df["FCST_UNITS"].iloc[0] if "FCST_UNITS" in df.columns else ""
    sid = df["OBS_SID"].iloc[0] if "OBS_SID" in df.columns else ""
    vx = df["VX_MASK"].iloc[0] if "VX_MASK" in df.columns else ""

    ax.set_xlabel("Valid Time (UTC)")
    ax.set_ylabel(f"{var} ({units})".strip())

    if title is None:
        # include init range for context
        inits = sorted(df["init"].unique())
        init_title = f"{inits[0]}–{inits[-1]}" if len(inits) > 1 else inits[0]
        title = f"{var} vs Obs at station {sid} by valid time ({vx}); inits {init_title}"
    ax.set_title(title)

    ax.grid(True, alpha=0.3)
    ax.legend(ncol=2)
    fig.autofmt_xdate()

    outfile = Path(outfile)
    fig.savefig(outfile, dpi=150, bbox_inches="tight")
    print(f"Saved: {outfile}")

# -------
# Main
# -------

def main():
    ap = argparse.ArgumentParser(
        description="Plot MET Point-Stat MPR for multiple init cycles by VALID time (no aggregation)."
    )
    ap.add_argument("--base_dir", required=True, help="Base directory containing init subdirs like 2024050300/")
    ap.add_argument(
        "--inits",
        nargs="+",
        required=True,
        help="One or more init directory names, e.g., 2024050300 2024050312 2024050400 2024050412",
    )
    ap.add_argument("--file_var_token", required=True, help="Token in filename used for glob, e.g., AOD, PM10, PM25")
    ap.add_argument("--fcst_var", required=True, help="FCST_VAR value inside file, e.g., AOD, PM10, PM25")
    ap.add_argument("--station_id", required=True, help="OBS_SID station id to plot")
    ap.add_argument("--vx_mask", default="FULL", help="VX_MASK filter (default FULL)")
    ap.add_argument("--title", default=None, help="Optional plot title override")
    ap.add_argument("--outfile", default=None, help="Optional output image filename (PNG).")
    ap.add_argument("--print_matches", action="store_true", help="Print a quick summary of matches")
    args = ap.parse_args()

    files = collect_files_for_inits(args.base_dir, args.inits, args.file_var_token)
    if not files:
        raise FileNotFoundError(
            f"No files matched under {args.base_dir} for inits {args.inits} and token '{args.file_var_token}'."
        )

    mpr = read_point_stat_mpr(files)
    if mpr.empty:
        raise RuntimeError("No MPR rows were read from the matched files.")

    mpr = add_init_from_path(mpr)

    series = build_station_valid_series_multi(
        mpr_df=mpr,
        station_id=args.station_id,
        fcst_var=args.fcst_var,
        vx_mask=args.vx_mask,
    )

    if args.print_matches:
        print(f"Inits requested: {args.inits}")
        print(f"Unique inits found in data: {sorted(series['init'].unique()) if not series.empty else 'NONE'}")
        print(f"Files matched: {len(files)}")
        print(f"MPR rows read: {len(mpr)}")
        print(f"Rows after filters (station/var/mask): {len(series)}")
        if not series.empty:
            print(series[["init", "FCST_VALID_BEG", "FCST", "OBS", "source_file"]].head(12))

    # Default output name if not specified
    outfile = args.outfile
    if outfile is None:
        var = args.fcst_var
        sid = args.station_id
        inits_sorted = sorted(args.inits)
        init_a, init_b = inits_sorted[0], inits_sorted[-1]
        outfile = f"mpr_fcst_v_obs_valid_{var}_{sid}_{init_a}_to_{init_b}.png"

    plot_fcst_obs_by_valid(series, title=args.title, outfile=outfile)


if __name__ == "__main__":
    main()
