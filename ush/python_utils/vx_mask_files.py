"""
Functions for getting the paths to the files that define the verification masks (the regions to
verify over) listed in VX_MASKS, and for checking the verification mask settings.
"""

import logging
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
        empty), the directory vx_masks under METPLUS_PARMdir containing the mask files that
        come with the workflow, and the directory share/met/poly in the MET installation
        (MET_INSTALL_DIR).
    """
    vx_mask_dirs = []
    if cfg["verification"]["VX_MASK_DIR"]:
        vx_mask_dirs.append(cfg["verification"]["VX_MASK_DIR"])
    vx_mask_dirs.append(os.path.join(cfg["user"]["METPLUS_PARMdir"], "vx_masks"))
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


def check_vx_mask_settings(cfg) -> None:
    """Check the verification mask settings VX_MASK_DIR and VX_MASKS.

    Check that VX_MASK_DIR, if set, is an absolute path to an existing directory, and that a file
    can be found for each mask in VX_MASKS (see get_file_for_each_vx_mask()).  If a mask has a file
    in more than one of the directories searched, log (at level INFO) which one is used.

    Parameters
    ----------
    cfg : dict
        The experiment configuration.

    Raises
    ------
    ValueError
        If VX_MASK_DIR is a relative path, or if a directory contains both <name>.poly and
        <name>.nc for a mask in VX_MASKS.
    FileNotFoundError
        If VX_MASK_DIR is not an existing directory, or if no file is found for a mask in
        VX_MASKS.
    """
    logger = logging.getLogger(__name__)
    vx_mask_dir = cfg["verification"]["VX_MASK_DIR"]
    if vx_mask_dir:
        # The verification tasks are launched from other directories, so if a
        # relative path is specified for vx_mask_dir that is correct from the
        # directory in which the experiment is generated, it would probably
        # point to the wrong location from within the verification tasks.  For
        # this reason, we don't allow vx_mask_dir (i.e. VX_MASK_DIR) to contain
        # a relative path; it must be absolute.
        if not os.path.isabs(vx_mask_dir):
            raise ValueError(
                f"VX_MASK_DIR must be an absolute path, but it is: {vx_mask_dir}\nTo specify a "
                "directory in the clone of the workflow, use the top-level directory of the "
                "clone, i.e. user.HOMEdir, in the value of VX_MASK_DIR, e.g. "
                "'{{ user.HOMEdir }}/my_masks'.")
        if not os.path.isdir(vx_mask_dir):
            raise FileNotFoundError(f"VX_MASK_DIR is not an existing directory: {vx_mask_dir}")
    # The following call to get_file_for_each_vx_mask() raises an error if no
    # file is found for any one of the masks in VX_MASKS, or if a directory
    # contains more than one file for a mask.  If all goes well, it returns a
    # list containing the path to each mask's .poly or .nc file, but that
    # return value is not needed here (the individual task scripts call
    # get_file_for_each_vx_mask() again when the tasks run).
    get_file_for_each_vx_mask(cfg)
    # If a mask has a file in more than one of the directories searched, say
    # which one is used, in case the user didn't intend the others to be
    # overridden.
    vx_mask_dirs = get_vx_mask_dirs(cfg)
    for mask in cfg["verification"]["VX_MASKS"]:
        paths_found = find_all_files_for_single_vx_mask(vx_mask_dirs, mask)
        if len(paths_found) > 1:
            paths_not_used = "\n  ".join(paths_found[1:])
            logger.info(
                f'The verification mask "{mask}" has a file in more than one of the directories '
                f"searched.  Using the first one found:\n  {paths_found[0]}\nand not:\n  "
                f"{paths_not_used}")
