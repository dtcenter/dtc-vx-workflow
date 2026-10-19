"""
Function for getting the settings associated with a single forecast (ensemble) member.
"""

from typing import NamedTuple


class EnsmemInfo(NamedTuple):
    """Settings associated with a single forecast (ensemble) member."""
    index: int
    """Index of the member (from ENSMEM_INDX_MIN to ENSMEM_INDX_MAX)."""
    pos: int
    """Position (0-based) of the member in the per-member lists FCST_FN_TEMPLATE and
    ENS_TIME_LAG_HRS."""
    name: str
    """Name of the member (e.g. mem001) used in task names, flag files, and output paths, and
    available as ${ensmem_name} in FCST_FN_TEMPLATE."""
    time_lag: int
    """Time lag of the member, in seconds."""
    fcst_fn_template: str
    """Forecast file name template for the member (not yet substituted)."""


def get_ensmem_info(cfg, ensmem_index: int) -> EnsmemInfo:
    """Get the settings associated with a single forecast (ensemble) member.

    The members are numbered consecutively from ENSMEM_INDX_MIN to ENSMEM_INDX_MAX.  The
    per-member lists FCST_FN_TEMPLATE and ENS_TIME_LAG_HRS contain one entry per member, in that
    order, so the entry for a given member is at position ensmem_index - ENSMEM_INDX_MIN.  For a
    deterministic forecast, there is a single member, with index ENSMEM_INDX_MIN.

    Parameters
    ----------
    cfg : dict-like
        The experiment configuration (must contain the "ensemble" and "verification" sections).
    ensmem_index : int
        Index of the member.

    Returns
    -------
    EnsmemInfo
        The member's index, position in the per-member lists, name, time lag (in seconds),
        and forecast file name template.

    Raises
    ------
    ValueError
        If ensmem_index is not between ENSMEM_INDX_MIN and ENSMEM_INDX_MAX.
    """
    enscfg = cfg["ensemble"]
    vxcfg = cfg["verification"]

    indx_min = enscfg["ENSMEM_INDX_MIN"]
    indx_max = enscfg["ENSMEM_INDX_MAX"]
    if not indx_min <= ensmem_index <= indx_max:
        raise ValueError(
            f"Ensemble member index ({ensmem_index}) must be between ENSMEM_INDX_MIN "
            f"({indx_min}) and ENSMEM_INDX_MAX ({indx_max})"
        )
    pos = ensmem_index - indx_min

    return EnsmemInfo(
        index=ensmem_index,
        pos=pos,
        name=f"mem{str(ensmem_index).zfill(vxcfg['VX_NDIGITS_ENSMEM_NAMES'])}",
        time_lag=int(enscfg["ENS_TIME_LAG_HRS"][pos]) * 3600,
        fcst_fn_template=vxcfg["FCST_FN_TEMPLATE"][pos],
    )
