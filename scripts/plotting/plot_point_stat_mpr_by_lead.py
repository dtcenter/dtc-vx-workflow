#!/usr/bin/env python3
"""
Plot MET Point-Stat MPR for a single model init cycle by forecast lead time (no aggregation).

Example:
  python plot_point_stat_mpr_by_lead.py \
    --base_dir /path/to/output \
    --init 2024050300 \
    --file_var_token PM10 \
    --fcst_var PM10 \
    --station_id 483550034  \
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
    # MET: YYYYMMDD_HHMMSS
    return pd.to_datetime(s, format="%Y%m%d_%H%M%S", errors="coerce")


def lead_to_hours(lead_str: str) -> float:
    """
    MET lead looks like HHMMSS (e.g., 140000 -> 14h, 720000 -> 72h).
    """
    s = str(lead_str)
    if len(s) != 6 or not s.isdigit():
        return float("nan")
    hh = int(s[0:2])
    mm = int(s[2:4])
    ss = int(s[4:6])
    return hh + mm / 60.0 + ss / 3600.0

def format_init_time(init_str: str):
    """
    Convert init like '2024050300' into:
      - title string: '2024-05-03 00Z'
      - filename string: '20240503_00Z'
    """
    dt = pd.to_datetime(init_str, format="%Y%m%d%H")
    title_str = dt.strftime("%Y-%m-%d %HZ")
    fname_str = dt.strftime("%Y%m%d_%HZ")
    return title_str, fname_str

def read_point_stat_mpr(files: Union[str, Path, Iterable[Union[str, Path]]]) -> pd.DataFrame:
    """
    Read one or many MET Point-Stat .stat files and return ONLY MPR lines as a DataFrame.
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

    #print(file_list)

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

    # Get the columns we actually need for plotting
    for c in ["FCST", "OBS", "OBS_LAT", "OBS_LON", "OBS_LVL", "OBS_ELV"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].replace("NA", pd.NA), errors="coerce")

    for c in ["FCST_VALID_BEG", "FCST_VALID_END", "OBS_VALID_BEG", "OBS_VALID_END"]:
        if c in df.columns:
            df[c] = df[c].apply(_parse_met_time)

    return df


# --------------------------------------
# File collection (single init, for now)
# --------------------------------------

def collect_files_for_init(
    base_dir: Union[str, Path],
    init: str,                   # e.g., "2024050300"
    file_var_token: str,         # var in filename: "AOD", "PM10", "PM25"
) -> List[Path]:
    """
    Collect Point-Stat .stat files in base_dir/init/ that contain _{file_var_token}_ and end in .stat.
    Note: This is assuming a pretty strict dir structure. Should build this out.
    """
    init_dir = Path(base_dir) / init
    if not init_dir.is_dir():
        raise FileNotFoundError(f"Init directory not found: {init_dir}")

    glob_pat = f"*_{file_var_token}_??????L_*V.stat"
    return sorted(init_dir.glob(glob_pat))


# ----------------------------------------------
# Filter + prepare for plotting (NO aggregation)
# ----------------------------------------------

def build_station_lead_series(
    mpr_df: pd.DataFrame,
    station_id: str,
    fcst_var: str,
    vx_mask: str = "FULL",
) -> pd.DataFrame:
    """
    Filter to one station/variable/mask and return rows sorted by lead_hr.
    No aggregation: one point per lead (if present).
    """
    if mpr_df.empty:
        return mpr_df

    df = mpr_df.copy()

    df = df[df["VX_MASK"].astype(str) == str(vx_mask)]
    df = df[df["FCST_VAR"].astype(str) == str(fcst_var)]
    df = df[df["OBS_SID"].astype(str) == str(station_id)]

    if df.empty:
        return df

    df["lead_hr"] = df["FCST_LEAD"].apply(lead_to_hours)

    # Keep one row per lead if duplicates exist (rare, but can happen with multiple matches).
    # This needs to be updated to fail...but for now, I will only plot what I know to be unique.
    df = df.sort_values(["lead_hr", "FCST_VALID_BEG"]).drop_duplicates(subset=["lead_hr"], keep="first")

    return df.reset_index(drop=True)

def plot_fcst_obs_by_lead(
    df: pd.DataFrame,
    init: str,
    title: Optional[str] = None,
#    outfile: Optional[str] = None,
):

    if df.empty:
        raise ValueError("No matching records after filtering (station/var/vx_mask).")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["lead_hr"], df["FCST"], marker="o", label="Forecast")
    ax.plot(df["lead_hr"], df["OBS"], marker="o", label="Obs")

    var = df["FCST_VAR"].iloc[0] if "FCST_VAR" in df.columns else ""
    units = df["FCST_UNITS"].iloc[0] if "FCST_UNITS" in df.columns else ""
    sid = df["OBS_SID"].iloc[0] if "OBS_SID" in df.columns else ""
    vx = df["VX_MASK"].iloc[0] if "VX_MASK" in df.columns else ""

    ax.set_xlabel("Forecast Lead (hours)")
    ax.set_ylabel(f"{var} ({units})".strip())

    print(init)
    init_title, init_fname = format_init_time(init)

    if title is None:
        title = f"{var} vs Obs at station {sid} by lead ({init_title})"
    ax.set_title(title)

    ax.grid(True, alpha=0.3)
    ax.legend()
#    plt.show()

    # Save figure
    fig_name = f"mpr_fcst_v_obs_{var}_{sid}_{init_fname}.png"
    plt.savefig(fig_name)


# ----------------------------
# Main
# ----------------------------

def main():
    ap = argparse.ArgumentParser(description="Plot MET Point-Stat MPR for one init cycle by lead time (no aggregation).")
    ap.add_argument("--base_dir", required=True, help="Base directory containing init subdirs like 2024050300/")
    ap.add_argument("--init", required=True, help="Init directory name, e.g., 2024050300")
    ap.add_argument("--file_var_token", required=True, help="Token in filename used for glob, e.g., AOD, PM10, PM25")
    ap.add_argument("--fcst_var", required=True, help="FCST_VAR value inside file, e.g., AOD, PM10, PM25")
    ap.add_argument("--station_id", required=True, help="OBS_SID station id to plot")
    ap.add_argument("--vx_mask", default="FULL", help="VX_MASK filter (default FULL)")
    ap.add_argument("--title", default=None, help="Optional plot title override")
    ap.add_argument("--print_matches", action="store_true", help="Print a quick summary of matches")
    args = ap.parse_args()

    files = collect_files_for_init(args.base_dir, args.init, args.file_var_token)
    if not files:
        raise FileNotFoundError(
            f"No files matched in {Path(args.base_dir)/args.init} for token '{args.file_var_token}'."
        )

    mpr = read_point_stat_mpr(files)
    series = build_station_lead_series(
        mpr_df=mpr,
        station_id=args.station_id,
        fcst_var=args.fcst_var,
        vx_mask=args.vx_mask,
    )

    if args.print_matches:
        print(f"Init: {args.init}")
        print(f"Files matched: {len(files)}")
        print(f"MPR rows read: {len(mpr)}")
        print(f"Rows after filters (station/var/mask): {len(series)}")
        if not series.empty:
            print(series[["lead_hr", "FCST", "OBS", "FCST_VALID_BEG", "source_file"]].head(10))

    plot_fcst_obs_by_lead(series, init=args.init, title=args.title)


if __name__ == "__main__":
    main()

