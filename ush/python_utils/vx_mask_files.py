"""
Function for getting the paths to the files that define the verification masks (the regions to
verify over) listed in VX_MASKS.
"""

import os

# Extensions of the mask files to look for: a .poly file is a list of the
# latitudes and longitudes of the corners of a polygon, and a .nc file is a
# NetCDF file containing a gridded mask, e.g. one made by MET's gen_vx_mask
# tool.  A directory may not contain files with both extensions for the same
# mask.
VX_MASK_FILE_EXTENSIONS = (".poly", ".nc")


def get_vx_mask_dirs(cfg) -> list[str]:
    """Get the directories in which to look for the verification mask files, in the order in
    which they are searched.

    Parameters
    ----------
    cfg : dict
        The experiment configuration.

    Returns
    -------
    list[str]
        The directory VX_MASK_DIR containing the user's mask files (if it is set, i.e. not
        empty), the directory metplus/vx_masks under PARMdir containing the mask files that
        come with the workflow, and the directory share/met/poly in the MET installation
        (MET_INSTALL_DIR).
    """
    vx_mask_dirs = []
    if cfg["verification"]["VX_MASK_DIR"]:
        vx_mask_dirs.append(cfg["verification"]["VX_MASK_DIR"])
    vx_mask_dirs.append(os.path.join(cfg["user"]["PARMdir"], "metplus", "vx_masks"))
    vx_mask_dirs.append(os.path.join(cfg["platform"]["MET_INSTALL_DIR"], "share", "met", "poly"))
    return vx_mask_dirs


def find_all_files_for_single_vx_mask(vx_mask_dirs: list[str], mask: str) -> list[str]:
    """Find the files for a verification mask in the given directories.

    Parameters
    ----------
    vx_mask_dirs : list[str]
        The directories to look in, e.g. as returned by get_vx_mask_dirs().
    mask : str
        The name of the mask.

    Returns
    -------
    list[str]
        The path to the file <mask>.poly or <mask>.nc in each directory that contains one, in
        the order of vx_mask_dirs.  The list is empty if no directory contains either file.

    Raises
    ------
    ValueError
        If a directory contains both <mask>.poly and <mask>.nc.
    """
    paths_found = []
    for vx_mask_dir in vx_mask_dirs:
        paths_to_try = [os.path.join(vx_mask_dir, f"{mask}{ext}")
                        for ext in VX_MASK_FILE_EXTENSIONS]
        paths_in_dir = [path for path in paths_to_try if os.path.isfile(path)]
        if len(paths_in_dir) > 1:
            raise ValueError(
                f'The directory {vx_mask_dir} contains more than one file for the verification '
                f'mask "{mask}":\n  ' + "\n  ".join(paths_in_dir) + "\nRemove or rename all "
                "but one of them.")
        # At this point, paths_in_dir contains the path to the mask's .poly or
        # .nc file in this directory, or is empty if there is neither.  Add it
        # to the paths found in the earlier directories.
        paths_found.extend(paths_in_dir)
    return paths_found


def get_file_for_each_vx_mask(cfg) -> list[str]:
    """Get the paths to the files that define the verification masks listed in VX_MASKS.

    For each mask name in VX_MASKS, look for the file <name>.poly or <name>.nc in each of the
    directories returned by get_vx_mask_dirs(), in order, and use the first file found.  Thus,
    a file in VX_MASK_DIR takes precedence over a file of the same name that comes with the
    workflow or with MET.

    Parameters
    ----------
    cfg : dict
        The experiment configuration.

    Returns
    -------
    list[str]
        The path to the file for each mask in VX_MASKS, in the same order as in VX_MASKS.  The list
        is empty if VX_MASKS is empty.

    Raises
    ------
    FileNotFoundError
        If no file is found for a mask in VX_MASKS.  The message lists the directories searched.
    ValueError
        If a directory contains both <name>.poly and <name>.nc for a mask in VX_MASKS (see
        find_all_files_for_single_vx_mask()).
    """
    vx_mask_dirs = get_vx_mask_dirs(cfg)
    vx_mask_files = []
    for mask in cfg["verification"]["VX_MASKS"]:
        # paths_found contains at most one path per directory in vx_mask_dirs.
        paths_found = find_all_files_for_single_vx_mask(vx_mask_dirs, mask)
        if not paths_found:
            raise FileNotFoundError(
                f'No file {mask}.poly or {mask}.nc found for the verification mask "{mask}" in '
                "VX_MASKS.  The following directories were searched, in this order:\n  "
                + "\n  ".join(vx_mask_dirs))
        vx_mask_files.append(paths_found[0])
    return vx_mask_files
