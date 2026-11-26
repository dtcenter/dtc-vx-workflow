"""
Functions for getting the paths to the files that define the verification masks (the regions to
verify over) listed in VX_MASKS, and for checking the verification mask settings.
"""

import logging
import os
import subprocess
import tempfile

# Extensions of the mask files to look for: a .poly file is a list of the
# latitudes and longitudes of the corners of a polygon, and a .nc file is a
# NetCDF file containing a gridded mask, e.g. one made by MET's gen_vx_mask
# tool.  A directory may not contain files with both extensions for the same
# mask.
VX_MASK_FILE_EXTENSIONS = (".poly", ".nc")

# The keyword that MET's mask.grid config entry accepts for the whole
# verification domain.  It is not the name of a grid, so MET's tools (e.g.
# gen_vx_mask) don't accept it where a grid is expected.
FULL_DOMAIN_MASK_NAME = "FULL"

# A grid built into MET (the NCEP grid G212), used to check that MET's
# gen_vx_mask tool works (see check_gen_vx_mask_works()).
KNOWN_MET_GRID_NAME = "G212"


def get_vx_mask_dirs(cfg, include_met_dir: bool = True) -> list[str]:
    """Get the directories in which to look for the verification mask files, in the order in
    which they are searched.

    Parameters
    ----------
    cfg : dict
        The experiment configuration.
    include_met_dir : bool, optional
        Whether to include the directory share/met/poly in the MET installation.  The default
        is True.

    Returns
    -------
    list[str]
        The directory VX_MASK_DIR containing the user's mask files (if it is set, i.e. not
        empty), the directory vx_masks under METPLUS_PARMdir containing the mask files that
        come with the workflow, and, if include_met_dir is True, the directory share/met/poly
        in the MET installation (MET_INSTALL_DIR).
    """
    vx_mask_dirs = []
    if cfg["verification"]["VX_MASK_DIR"]:
        vx_mask_dirs.append(cfg["verification"]["VX_MASK_DIR"])
    vx_mask_dirs.append(os.path.join(cfg["user"]["METPLUS_PARMdir"], "vx_masks"))
    if include_met_dir:
        vx_mask_dirs.append(
            os.path.join(cfg["platform"]["MET_INSTALL_DIR"], "share", "met", "poly"))
    return vx_mask_dirs


def is_met_builtin_grid(cfg, name: str) -> bool:
    """Check whether a name is that of a grid built into MET, e.g. the NCEP grid G212.

    MET has no tool that lists its built-in grids, so this runs MET's gen_vx_mask tool with the
    name as its input grid and as its mask (with "-type grid").  gen_vx_mask succeeds (exit status
    0) if the name is a built-in grid, and fails otherwise.  It treats a name that is not a
    built-in grid as the path to a file, so it is run in a new, empty temporary directory, in
    which no such file can exist.  In that case, gen_vx_mask fails (exits with a non-zero
    status), and this function returns False.

    Parameters
    ----------
    cfg : dict
        The experiment configuration.  MET_INSTALL_DIR in its platform section is the MET
        installation whose gen_vx_mask is run.
    name : str
        The name to check.

    Returns
    -------
    bool
        True if the name is a grid built into MET, and False otherwise.

    Raises
    ------
    FileNotFoundError
        If gen_vx_mask is not in the bin directory of the MET installation.
    """
    met_install_dir = cfg["platform"]["MET_INSTALL_DIR"]
    gen_vx_mask = os.path.join(met_install_dir, "bin", "gen_vx_mask")
    if not os.path.isfile(gen_vx_mask):
        raise FileNotFoundError(
            "MET's gen_vx_mask tool, which is needed to check whether the verification mask "
            f"files have reserved names, was not found at:\n  {gen_vx_mask}")
    #
    # MET's tools read their config files from MET_BASE (the share/met
    # directory of the MET installation) if it is set.  Set it to that of the
    # installation whose gen_vx_mask is run, so that a MET_BASE left in the
    # environment for another installation is not used.  The line below
    # builds the environment that gen_vx_mask runs in (it is passed to
    # subprocess.run() as env):
    #
    # - dict(os.environ, ...) makes a copy of the current process's
    #   environment variables, so PATH, LD_LIBRARY_PATH, etc. carry over.
    #
    # - MET_BASE=... sets MET_BASE in that copy to
    #   <MET_INSTALL_DIR>/share/met, replacing any MET_BASE already there.
    #   (dict(mapping, key=value) copies the mapping and then adds or
    #   overrides the keyword arguments.)
    #
    # - os.environ itself isn't changed, so the rest of experiment generation
    #   doesn't see the new MET_BASE; only the gen_vx_mask process does.
    #
    env = dict(os.environ, MET_BASE=os.path.join(met_install_dir, "share", "met"))
    #
    # gen_vx_mask takes three positional arguments, "input_grid mask_file
    # out_file", followed by options:
    #
    # - input_grid is the grid on which the output mask is defined: a grid
    #   built into MET, a gridded data file, or a grid specification string.
    #
    # - mask_file defines the region to mask.  What it is depends on the
    #   -type option, e.g. a .poly file for "-type poly", or, for
    #   "-type grid", a grid (given in any of the ways input_grid can be)
    #   whose area is the region included in the mask to be generated.
    #
    # - out_file is the NetCDF mask file that gen_vx_mask writes.  Here, it is
    #   written in the temporary directory, which is deleted with everything
    #   in it at the end of the "with" block.
    #
    # - "-v 0" sets the verbosity of gen_vx_mask's log messages to 0 (the
    #   fewest messages).
    #
    # Usually, input_grid and mask_file differ, e.g.
    #
    #   gen_vx_mask G212 G218 out.nc -type grid
    #
    # makes a mask on grid G212 of the points that are inside the area of grid
    # G218.  Below, the name being checked is passed as both, only because the
    # output isn't needed.  Whatever mask_file is, gen_vx_mask must first read
    # input_grid as a grid, and whether it can is the only question being
    # asked.  With the same name for both, the run is guaranteed to succeed if
    # the name is a grid built into MET.  If it isn't, MET fails while reading
    # input_grid.
    #
    with tempfile.TemporaryDirectory() as tmp_dir:
        result = subprocess.run(
            [gen_vx_mask, name, name, os.path.join(tmp_dir, "mask.nc"), "-type", "grid",
             "-v", "0"],
            cwd=tmp_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False)
    return result.returncode == 0


def check_gen_vx_mask_works(cfg) -> None:
    """Check that MET's gen_vx_mask tool works, i.e. that is_met_builtin_grid() returns True for
    a grid known to be built into MET (KNOWN_MET_GRID_NAME).  If gen_vx_mask fails for every
    name, e.g. because a shared library it needs is missing, is_met_builtin_grid() returns False
    for every name, and no name would be found to be that of a built-in grid.

    Parameters
    ----------
    cfg : dict
        The experiment configuration.

    Raises
    ------
    RuntimeError
        If is_met_builtin_grid() returns False for KNOWN_MET_GRID_NAME.
    FileNotFoundError
        If gen_vx_mask is not found (see is_met_builtin_grid()).
    """
    if not is_met_builtin_grid(cfg, KNOWN_MET_GRID_NAME):
        gen_vx_mask = os.path.join(cfg["platform"]["MET_INSTALL_DIR"], "bin", "gen_vx_mask")
        raise RuntimeError(
            f"MET's gen_vx_mask tool did not recognize \"{KNOWN_MET_GRID_NAME}\", a grid built "
            f"into MET, so it does not seem to work.  Check that it runs, e.g. with:\n  "
            f"{gen_vx_mask} {KNOWN_MET_GRID_NAME} {KNOWN_MET_GRID_NAME} mask.nc -type grid")


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


def find_vx_mask_files_with_reserved_names(cfg) -> list[str]:
    """Find all verification mask files whose names (without the extension) are reserved,
    i.e. they are either equal to "FULL" (so that the name of the file is either FULL.poly or
    FULL.nc) or are names of grids built into MET.  Such mask file names are not allowed in the
    directory of masks that come with the dtc-vx-workflow (METPLUS_PARMdir/vx_masks) or in the
    user-specified masks directory VX_MASK_DIR (if it is set) because if they were ever
    specified in VX_MASKS, it would not be clear whether the user meant to use the mask file in
    one of those directories or the built-in grid (or, for FULL, the whole verification domain).

    The directories that are searched for such mask files are the ones that get_vx_mask_dirs()
    returns but with MET's share/met/poly excluded (since we can safely assume that any mask
    file that MET includes in its directory tree does not have a name that clashes with its
    built-in grids), i.e. the directories returned by

      get_vx_mask_dirs(cfg, include_met_dir=False)

    Currently, these are VX_MASK_DIR (if it is set) and METPLUS_PARMdir/vx_masks.  All the mask
    files in them are checked, whether or not they are listed in VX_MASKS.

    Parameters
    ----------
    cfg : dict
        The experiment configuration.

    Returns
    -------
    list[str]
        The paths to the files with reserved names, sorted.  The list is empty if there are none.

    Raises
    ------
    RuntimeError
        If MET's gen_vx_mask tool doesn't work (see check_gen_vx_mask_works()).
    FileNotFoundError
        If gen_vx_mask is not found (see is_met_builtin_grid()).
    """
    # Make sure that gen_vx_mask works before using it to check the names,
    # since otherwise no name would be found to be that of a built-in grid.
    check_gen_vx_mask_works(cfg)

    # Initialize the set that will contain the paths of the mask files whose
    # names are to be checked.
    mask_files_to_check = set()

    # Include in mask_files_to_check all the mask files in the directories
    # that are normally searched for masks (see get_vx_mask_dirs()), except
    # MET's share/met/poly.  Thus, all masks in these directories are checked
    # regardless of whether they are listed in VX_MASKS.
    dirs_to_scan = get_vx_mask_dirs(cfg, include_met_dir=False)
    for scanned_dir in dirs_to_scan:
        for entry in os.listdir(scanned_dir):
            # Get the full path to the current entry in the current directory.
            path = os.path.join(scanned_dir, entry)
            # Only consider as candidates for mask_files_to_check those
            # directory entries that are files or valid symlinks to files (not
            # subdirectories, broken symlinks, or other non-file entries).
            if os.path.isfile(path):
                # If the file's extension is one of those in
                # VX_MASK_FILE_EXTENSIONS (e.g. ".poly" or ".nc"), add the file
                # to the set of mask files to check for reserved names.
                file_ext = os.path.splitext(entry)[1]
                if file_ext in VX_MASK_FILE_EXTENSIONS:
                    mask_files_to_check.add(path)

    # Create a list of the paths to the mask files that have reserved names.
    # Note that there may be more than one path in mask_files_to_check with
    # the same mask name (because mask files with the same name, without the
    # extension, may exist in different directories).  To save computation,
    # check each unique mask name in mask_files_to_check only once.  The
    # dictionary is_reserved_name has as its keys the (unique) set of mask
    # names and as the corresponding values booleans specifying
    # whether or not each mask name is a reserved name.
    reserved_mask_name_paths = []
    is_reserved_name = {}
    for mask_path in mask_files_to_check:
        mask_name = os.path.splitext(os.path.basename(mask_path))[0]
        # Check whether the current mask name is reserved only if that mask
        # name hasn't already been checked.
        if mask_name not in is_reserved_name:
            is_reserved_name[mask_name] = (mask_name == FULL_DOMAIN_MASK_NAME
                                           or is_met_builtin_grid(cfg, mask_name))
        if is_reserved_name[mask_name]:
            reserved_mask_name_paths.append(mask_path)

    return sorted(reserved_mask_name_paths)


def check_vx_mask_settings(cfg) -> None:
    """Check the verification mask settings VX_MASK_DIR and VX_MASKS.

    Check that VX_MASK_DIR, if set, is an absolute path to an existing directory, that no mask file
    has a reserved name, i.e. "FULL" or the name of a grid built into MET (see
    find_vx_mask_files_with_reserved_names()), and that a file can be found for each mask in
    VX_MASKS (see get_file_for_each_vx_mask()).  If a mask has a file in more than one of the
    directories searched, log (at level INFO) which one is used.

    Parameters
    ----------
    cfg : dict
        The experiment configuration.

    Raises
    ------
    ValueError
        If VX_MASK_DIR is a relative path, if a mask file has a reserved name, or if a
        directory contains both <name>.poly and <name>.nc for a mask in VX_MASKS.
    FileNotFoundError
        If VX_MASK_DIR is not an existing directory, if no file is found for a mask in VX_MASKS,
        or if MET's gen_vx_mask tool is not found (see is_met_builtin_grid()).
    RuntimeError
        If MET's gen_vx_mask tool doesn't work (see check_gen_vx_mask_works()).
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

    files_with_reserved_names = find_vx_mask_files_with_reserved_names(cfg)
    if files_with_reserved_names:
        raise ValueError(
            "The following verification mask files have reserved names, "
            f'i.e. "{FULL_DOMAIN_MASK_NAME}" or the name of a grid built into MET (e.g. '
            f'"{KNOWN_MET_GRID_NAME}"):\n  ' + "\n  ".join(files_with_reserved_names)
            + "\nRename these files (and the masks in VX_MASKS that refer to them).")

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
