"""
Unit tests for get_vx_mask_dirs(), get_file_for_each_vx_mask(),
find_all_files_for_single_vx_mask(), is_met_builtin_grid(),
check_gen_vx_mask_works(), find_vx_mask_files_with_reserved_names() and
check_vx_mask_settings() in python_utils/vx_mask_files.py, and checks of the
mask files that come with the workflow in parm/metplus/vx_masks.

To run them, issue the following command from the top-level directory:
    UNIT_TEST=True PYTHONPATH=ush python3 -m unittest -b tests/test_python/test_vx_mask_files.py
"""

import os
import re
import tempfile
import unittest
from pathlib import Path

from python_utils import check_vx_mask_settings, get_file_for_each_vx_mask
from python_utils.vx_mask_files import (
    KNOWN_MET_GRID_NAME, VX_MASK_FILE_EXTENSIONS, check_gen_vx_mask_works,
    find_all_files_for_single_vx_mask, find_vx_mask_files_with_reserved_names,
    get_vx_mask_dirs, is_met_builtin_grid
)

TOP_DIR = Path(__file__).resolve().parents[2]

# The names that the fake gen_vx_mask made by TestVxMaskFiles.setUp() accepts
# as grids built into MET.  They are real MET grid names, one of each kind.
# The first is KNOWN_MET_GRID_NAME, which check_gen_vx_mask_works() uses to
# check that gen_vx_mask works, so the fake always recognizes it.
# The tests below that need a mask file named after a grid built into MET
# also use KNOWN_MET_GRID_NAME, so that they still work if it is changed.
FAKE_MET_GRIDS = (KNOWN_MET_GRID_NAME, "DTC165", "wwmca_north")

# A fake version of MET's gen_vx_mask tool, written as a shell script.  It
# exits with status 0 if its first argument (the input grid) is one of
# FAKE_MET_GRIDS, and 1 otherwise, as the real tool does when run with
# "-type grid".  It also checks how is_met_builtin_grid() runs it: it exits
# with status 2 if MET_BASE is not set, and 3 if the directory it is run in
# is not empty.
FAKE_GEN_VX_MASK = f"""#!/bin/sh
[ -n "$MET_BASE" ] || exit 2
[ -z "$(ls -A .)" ] || exit 3
case "$1" in
  {"|".join(FAKE_MET_GRIDS)}) exit 0 ;;
esac
exit 1
"""

# The reserved names that test_no_reserved_names (in TestWorkflowVxMasks)
# looks for in the mask files that come with the workflow: FULL, and the
# three kinds of names of grids built into MET 12 (e.g. G212, DTC165 and
# wwmca_north).  That test uses this pattern instead of gen_vx_mask because
# the real gen_vx_mask may not be available where the unit tests run (e.g.
# in the GitHub CI).
RESERVED_VX_MASK_NAME_REGEX = re.compile(r"^(FULL|G[0-9]{3}|DTC[0-9]{3}|wwmca_.*)$")


class TestVxMaskFiles(unittest.TestCase):
    """Tests for get_vx_mask_dirs(), get_file_for_each_vx_mask(),
    find_all_files_for_single_vx_mask(), is_met_builtin_grid(),
    check_gen_vx_mask_works(), find_vx_mask_files_with_reserved_names() and
    check_vx_mask_settings()."""

    # unittest calls setUp() automatically before each test method (each method
    # whose name starts with "test"), so each test starts with its own new,
    # empty set of directories.  The cleanup that setUp() registers with
    # addCleanup() deletes them automatically after the test, whether it
    # passes or fails.
    def setUp(self):
        """Creates, in a temporary directory, the three directories that are
        searched: a user mask directory (VX_MASK_DIR), a METplus parm
        directory (METPLUS_PARMdir) containing vx_masks, and a MET installation
        (MET_INSTALL_DIR) containing share/met/poly.  The MET installation
        also contains bin/gen_vx_mask, a fake version of the tool (see
        FAKE_GEN_VX_MASK)."""
        # pylint: disable=consider-using-with
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.user_dir = os.path.join(tmp_dir.name, "user_masks")
        self.metplus_parm_dir = os.path.join(tmp_dir.name, "parm", "metplus")
        self.wflow_mask_dir = os.path.join(self.metplus_parm_dir, "vx_masks")
        self.met_install_dir = os.path.join(tmp_dir.name, "met")
        self.met_poly_dir = os.path.join(self.met_install_dir, "share", "met", "poly")
        for d in (self.user_dir, self.wflow_mask_dir, self.met_poly_dir):
            os.makedirs(d)
        self.gen_vx_mask = os.path.join(self.met_install_dir, "bin", "gen_vx_mask")
        os.makedirs(os.path.dirname(self.gen_vx_mask))
        with open(self.gen_vx_mask, "w", encoding="utf-8") as f:
            f.write(FAKE_GEN_VX_MASK)
        # Make the script executable (mode rwxr-xr-x).
        os.chmod(self.gen_vx_mask, 0o755)

    def _make_cfg(self, vx_masks, vx_mask_dir=None):
        """Returns a minimal experiment configuration containing the settings
        used by get_file_for_each_vx_mask().  VX_MASK_DIR is set to the user
        mask directory unless vx_mask_dir is given ("" for unset)."""
        return {
            "verification": {
                "VX_MASKS": vx_masks,
                "VX_MASK_DIR": self.user_dir if vx_mask_dir is None else vx_mask_dir,
            },
            "user": {"METPLUS_PARMdir": self.metplus_parm_dir},
            "platform": {"MET_INSTALL_DIR": self.met_install_dir},
        }

    @staticmethod
    def _touch(path):
        """Creates an empty file at path and returns path."""
        with open(path, "w", encoding="utf-8"):
            pass
        return path

    def test_empty_vx_masks(self):
        """An empty VX_MASKS gives an empty list."""
        self.assertEqual(get_file_for_each_vx_mask(self._make_cfg([])), [])

    def test_each_directory(self):
        """A mask is found in each of the three directories, as a .poly or .nc
        file, and the paths are returned in the order of VX_MASKS."""
        expected = [
            self._touch(os.path.join(self.met_poly_dir, "CONUS.poly")),
            self._touch(os.path.join(self.user_dir, "OR_WA_CA.nc")),
            self._touch(os.path.join(self.wflow_mask_dir, "AZCA.poly")),
        ]
        cfg = self._make_cfg(["CONUS", "OR_WA_CA", "AZCA"])
        self.assertEqual(get_file_for_each_vx_mask(cfg), expected)

    def test_directory_precedence(self):
        """A file in an earlier directory takes precedence over one of the same
        name in a later directory: VX_MASK_DIR over parm/metplus/vx_masks over
        the MET installation.  find_all_files_for_single_vx_mask() returns all
        of them, in that order."""
        user_file = self._touch(os.path.join(self.user_dir, "WEST.poly"))
        wflow_file = self._touch(os.path.join(self.wflow_mask_dir, "WEST.poly"))
        met_file = self._touch(os.path.join(self.met_poly_dir, "WEST.poly"))
        cfg = self._make_cfg(["WEST"])
        self.assertEqual(find_all_files_for_single_vx_mask(get_vx_mask_dirs(cfg), "WEST"),
                         [user_file, wflow_file, met_file])
        self.assertEqual(get_file_for_each_vx_mask(cfg), [user_file])
        os.remove(user_file)
        self.assertEqual(get_file_for_each_vx_mask(cfg), [wflow_file])

    def test_nc_and_poly_in_different_dirs(self):
        """A .nc file in an earlier directory takes precedence over a .poly
        file of the same name in a later one."""
        nc_file = self._touch(os.path.join(self.user_dir, "EAST.nc"))
        self._touch(os.path.join(self.wflow_mask_dir, "EAST.poly"))
        self.assertEqual(get_file_for_each_vx_mask(self._make_cfg(["EAST"])), [nc_file])

    def test_poly_and_nc_in_same_dir(self):
        """A directory containing both a .poly and a .nc file for a mask raises
        ValueError, whose message names both files.  This happens even if an
        earlier directory contains a file for the mask, which would otherwise
        be used."""
        poly_file = self._touch(os.path.join(self.wflow_mask_dir, "EAST.poly"))
        nc_file = self._touch(os.path.join(self.wflow_mask_dir, "EAST.nc"))
        for user_file in (None, os.path.join(self.user_dir, "EAST.poly")):
            with self.subTest(user_file=user_file):
                if user_file:
                    self._touch(user_file)
                with self.assertRaises(ValueError) as ctx:
                    get_file_for_each_vx_mask(self._make_cfg(["EAST"]))
                self.assertIn(poly_file, str(ctx.exception))
                self.assertIn(nc_file, str(ctx.exception))

    def test_unset_vx_mask_dir(self):
        """With VX_MASK_DIR unset (empty), the user mask directory is not
        searched, and the other two directories still are."""
        self._touch(os.path.join(self.user_dir, "CONUS.poly"))
        met_file = self._touch(os.path.join(self.met_poly_dir, "CONUS.poly"))
        cfg = self._make_cfg(["CONUS"], vx_mask_dir="")
        self.assertEqual(get_file_for_each_vx_mask(cfg), [met_file])

    def test_missing_mask(self):
        """A mask with no file in any directory raises FileNotFoundError, whose
        message names the mask and lists the three directories searched."""
        cfg = self._make_cfg(["NOWHERE"])
        with self.assertRaises(FileNotFoundError) as ctx:
            get_file_for_each_vx_mask(cfg)
        msg = str(ctx.exception)
        self.assertIn('"NOWHERE"', msg)
        for d in (self.user_dir, self.wflow_mask_dir, self.met_poly_dir):
            self.assertIn(d, msg)

    def test_check_relative_vx_mask_dir(self):
        """check_vx_mask_settings() raises ValueError if VX_MASK_DIR is a
        relative path, even if that path exists relative to the current
        directory."""
        self._touch(os.path.join(self.met_poly_dir, "CONUS.poly"))
        cfg = self._make_cfg(["CONUS"], vx_mask_dir=os.path.relpath(self.user_dir))
        with self.assertRaises(ValueError) as ctx:
            check_vx_mask_settings(cfg)
        self.assertIn("VX_MASK_DIR must be an absolute path", str(ctx.exception))

    def test_check_missing_vx_mask_dir(self):
        """check_vx_mask_settings() raises FileNotFoundError if VX_MASK_DIR is
        not an existing directory."""
        self._touch(os.path.join(self.met_poly_dir, "CONUS.poly"))
        missing_dir = os.path.join(self.user_dir, "missing")
        cfg = self._make_cfg(["CONUS"], vx_mask_dir=missing_dir)
        with self.assertRaises(FileNotFoundError) as ctx:
            check_vx_mask_settings(cfg)
        self.assertIn(missing_dir, str(ctx.exception))

    def test_check_logs_overridden_mask(self):
        """check_vx_mask_settings() logs nothing if each mask has a file in
        only one directory, and logs a message at level INFO naming the file
        used and the file not used if a mask has a file in more than one."""
        met_file = self._touch(os.path.join(self.met_poly_dir, "WEST.poly"))
        cfg = self._make_cfg(["WEST"])
        # The name of the logger that check_vx_mask_settings() writes to.  The
        # function gets its logger with logging.getLogger(__name__), and
        # __name__ is the module's full import name, which is
        # "python_utils.vx_mask_files" because the tests run with
        # PYTHONPATH=ush.  It is put in a variable because both assertNoLogs()
        # and assertLogs() below use it.
        logger_name = "python_utils.vx_mask_files"
        # At this point, the only file for WEST is the one in the MET
        # installation, so check_vx_mask_settings() should log nothing.
        # assertNoLogs() (new in Python 3.10) is the opposite of assertLogs().
        # While the "with" block runs, it watches the logger named
        # logger_name:
        #
        # - It counts only the messages sent to that logger or its children
        #   (e.g. python_utils.vx_mask_files.something), not those sent to
        #   other loggers, including the root logger.
        #
        # - It counts only the messages at the given level (INFO) or higher
        #   (WARNING, ERROR, CRITICAL), not DEBUG messages.
        #
        # - When the block ends, the test fails ("Unexpected logs found") if
        #   any such message was logged.  The messages are captured, so they
        #   aren't printed.
        #
        # If logger_name were wrong (e.g. after the module is renamed),
        # nothing would ever be logged to it, so assertNoLogs() would pass
        # without checking anything.  The assertLogs() below protects against
        # that, since it fails if no message is logged to logger_name.
        with self.assertNoLogs(logger_name, level="INFO"):
            check_vx_mask_settings(cfg)
        user_file = self._touch(os.path.join(self.user_dir, "WEST.poly"))
        with self.assertLogs(logger_name, level="INFO") as ctx:
            check_vx_mask_settings(cfg)
        self.assertEqual(len(ctx.records), 1)
        msg = ctx.records[0].getMessage()
        self.assertIn('"WEST"', msg)
        # The file used comes before "and not:", and the one not used after.
        used, not_used = msg.split("and not:")
        self.assertIn(user_file, used)
        self.assertIn(met_file, not_used)

    def test_is_met_builtin_grid(self):
        """is_met_builtin_grid() returns True for the names that gen_vx_mask
        accepts as grids, and False for others, including FULL (which MET
        accepts only in mask.grid, not as a grid).  Since the fake
        gen_vx_mask fails with a different status if MET_BASE is not set or
        the directory it runs in is not empty, this also checks that
        is_met_builtin_grid() sets MET_BASE and runs it in an empty
        directory (which is how it's intended to be run)."""
        # All that is_met_builtin_grid() needs from cfg is the path to the
        # (fake) MET installation, MET_INSTALL_DIR, which _make_cfg() always
        # sets.  No masks are needed, so pass an empty list.
        cfg = self._make_cfg([])
        for name in FAKE_MET_GRIDS:
            with self.subTest(name=name):
                self.assertTrue(is_met_builtin_grid(cfg, name))
        for name in ("CONUS", "FULL", "G999"):
            with self.subTest(name=name):
                self.assertFalse(is_met_builtin_grid(cfg, name))

    def test_is_met_builtin_grid_without_gen_vx_mask(self):
        """is_met_builtin_grid() raises FileNotFoundError, whose message gives
        the path to gen_vx_mask, if the gen_vx_mask tool is not in the MET
        installation."""
        os.remove(self.gen_vx_mask)
        with self.assertRaises(FileNotFoundError) as ctx:
            is_met_builtin_grid(self._make_cfg([]), "G212")
        self.assertIn(self.gen_vx_mask, str(ctx.exception))

    def test_check_gen_vx_mask_works(self):
        """check_gen_vx_mask_works() doesn't raise an error if gen_vx_mask
        recognizes KNOWN_MET_GRID_NAME as a grid.  If gen_vx_mask fails for
        every name (as it would if it were broken, e.g. because a shared
        library is missing), it raises RuntimeError, whose message gives the
        path to gen_vx_mask.  The same is true of
        find_vx_mask_files_with_reserved_names(), since it calls
        check_gen_vx_mask_works()."""
        # The "works" case.  The list of masks doesn't matter here, so it is
        # empty.  The fake gen_vx_mask (created in setUp()) recognizes only
        # the names in FAKE_MET_GRIDS, which include KNOWN_MET_GRID_NAME, so
        # check_gen_vx_mask_works() must return without raising an error (if
        # it raised one, the test would fail).
        cfg = self._make_cfg([])
        check_gen_vx_mask_works(cfg)
        # Replace the fake gen_vx_mask with another fake one that fails for
        # every name, to simulate a real gen_vx_mask that can't run (e.g.
        # because a shared library is missing).  Opening the existing file
        # with "w" replaces its contents but keeps its permissions, so it
        # stays executable.  setUp() creates a new fake for each test, so
        # other tests aren't affected by this replacement.
        with open(self.gen_vx_mask, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nexit 1\n")
        # The "doesn't work" case.  check_gen_vx_mask_works() must raise a
        # RuntimeError, and its message must give the path to gen_vx_mask so
        # that the user knows which tool to check.
        with self.assertRaises(RuntimeError) as ctx:
            check_gen_vx_mask_works(cfg)
        self.assertIn(self.gen_vx_mask, str(ctx.exception))
        # The function find_vx_mask_files_with_reserved_names() must call
        # check_gen_vx_mask_works() and so raise the same error.  Without that
        # call, the broken gen_vx_mask would recognize no name as a grid, and
        # the function would return an empty list.  The mask file CONUS.poly
        # created here isn't needed for the error (the check runs even if
        # there are no mask files), but it gives the function a name that the
        # broken gen_vx_mask would otherwise have let pass.
        self._touch(os.path.join(self.wflow_mask_dir, "CONUS.poly"))
        with self.assertRaises(RuntimeError):
            find_vx_mask_files_with_reserved_names(cfg)

    def test_vx_mask_dirs_without_met_dir(self):
        """get_vx_mask_dirs() leaves out the MET installation's share/met/poly
        if include_met_dir is False, with or without VX_MASK_DIR set."""
        cfg = self._make_cfg([])
        self.assertEqual(get_vx_mask_dirs(cfg),
                         [self.user_dir, self.wflow_mask_dir, self.met_poly_dir])
        self.assertEqual(get_vx_mask_dirs(cfg, include_met_dir=False),
                         [self.user_dir, self.wflow_mask_dir])
        cfg = self._make_cfg([], vx_mask_dir="")
        self.assertEqual(get_vx_mask_dirs(cfg, include_met_dir=False), [self.wflow_mask_dir])

    def test_files_with_reserved_names(self):
        """find_vx_mask_files_with_reserved_names() finds the mask files whose
        names are reserved, i.e. that are named "FULL" or have the same
        name as a grid built into MET, in VX_MASK_DIR and parm/metplus/vx_masks
        but not in the MET installation (MET_INSTALL_DIR/share/met/poly).  It
        returns their paths, sorted, whether or not those masks are listed in
        VX_MASKS (i.e. regardless of the list of masks passed to _make_cfg()
        below), and doesn't return files with other names."""
        full_file = self._touch(os.path.join(self.user_dir, "FULL.poly"))
        grid_file = self._touch(os.path.join(self.wflow_mask_dir, f"{KNOWN_MET_GRID_NAME}.nc"))
        self._touch(os.path.join(self.user_dir, "CONUS.poly"))
        self._touch(os.path.join(self.met_poly_dir, "DTC165.poly"))
        self.assertEqual(find_vx_mask_files_with_reserved_names(self._make_cfg(["CONUS"])),
                         sorted([full_file, grid_file]))
        self.assertEqual(find_vx_mask_files_with_reserved_names(self._make_cfg(["DTC165"])),
                         sorted([full_file, grid_file]))
        # With VX_MASK_DIR unset, the files in the user directory aren't
        # checked.
        cfg = self._make_cfg(["CONUS"], vx_mask_dir="")
        self.assertEqual(find_vx_mask_files_with_reserved_names(cfg), [grid_file])

    def test_files_with_same_reserved_name(self):
        """find_vx_mask_files_with_reserved_names() returns a sorted list of the
        paths (as strings) to all the mask files whose names (without the
        extension) are reserved.  For a given reserved name (e.g.
        "G212"), it returns the paths to all the files with that name in all
        the directories it checks, whatever their extension.  For example, if
        VX_MASK_DIR contains G212.poly and parm/metplus/vx_masks contains
        G212.nc and G212.poly, all three paths are returned.  The setting of
        VX_MASKS in the experiment config (i.e. the list of masks passed to
        _make_cfg() below) doesn't affect the result."""
        expected = sorted([
            self._touch(os.path.join(self.user_dir, f"{KNOWN_MET_GRID_NAME}.poly")),
            self._touch(os.path.join(self.wflow_mask_dir, f"{KNOWN_MET_GRID_NAME}.nc")),
            self._touch(os.path.join(self.wflow_mask_dir, f"{KNOWN_MET_GRID_NAME}.poly")),
        ])
        self.assertEqual(find_vx_mask_files_with_reserved_names(self._make_cfg(["CONUS"])),
                         expected)

    def test_check_files_with_reserved_names(self):
        """check_vx_mask_settings() raises ValueError, whose message lists the
        files, if a mask file in one of the directories checked has a reserved
        name, even if that mask is not listed in VX_MASKS."""
        self._touch(os.path.join(self.met_poly_dir, "CONUS.poly"))
        grid_file = self._touch(os.path.join(self.user_dir, "wwmca_north.poly"))
        with self.assertRaises(ValueError) as ctx:
            check_vx_mask_settings(self._make_cfg(["CONUS"]))
        self.assertIn("reserved names", str(ctx.exception))
        self.assertIn(grid_file, str(ctx.exception))


class TestWorkflowVxMasks(unittest.TestCase):
    """Tests of the mask files that come with the workflow."""

    def test_one_file_per_mask(self):
        """No mask in parm/metplus/vx_masks has more than one file, i.e. both
        a .poly and a .nc file.  This checks every mask in the directory, not
        only those listed in an experiment's VX_MASKS."""
        wflow_mask_dir = TOP_DIR / "parm" / "metplus" / "vx_masks"
        # wflow_mask_dir.iterdir() yields a Path object for each entry (file
        # or subdirectory) in wflow_mask_dir, the pathlib version of
        # os.listdir():
        #
        # - Each Path is the full path to the entry, e.g.
        #   .../vx_masks/AZCA.poly, not just its name.
        #
        # - Only the entries directly in wflow_mask_dir are listed, not the
        #   contents of its subdirectories, and "." and ".." are not included.
        #
        # - The entries come in no particular order (whatever order the file
        #   system returns them in).
        #
        # - It is a generator, so the entries are read one at a time as the
        #   set comprehension asks for them.
        #
        # - If wflow_mask_dir does not exist, it raises FileNotFoundError, so
        #   the test reports an error instead of passing.
        #
        # The set comprehension keeps the name (path.stem, e.g. "AZCA") of each
        # entry whose extension (path.suffix, e.g. ".poly") is that of a mask
        # file, and keeps each name only once, even if the mask has both a
        # .poly and a .nc file.  sorted() puts the names in alphabetical
        # order, so the masks are checked in the same order every time.
        masks = sorted({path.stem for path in wflow_mask_dir.iterdir()
                        if path.suffix in VX_MASK_FILE_EXTENSIONS})
        # Make sure the test doesn't pass just because it found no masks, e.g.
        # because the directory was renamed and an empty one left behind.
        # assertTrue(x, msg) passes if bool(x) is True, and fails otherwise.
        self.assertTrue(masks, f"No mask files found in {wflow_mask_dir}")
        for mask in masks:
            # subTest() runs each pass through the loop as a separate sub-test.
            # An exception or failed assertion inside the "with" block ends only
            # that sub-test, and the loop goes on to the next mask, so every
            # mask with more than one file is reported, not just the first.
            # (Without subTest(), the first exception would end the whole test
            # method.)  The keyword argument mask=mask labels the sub-test: the
            # report shows it after the test name, e.g. "(mask='AZCA')", so it
            # is clear which mask the result is for.  The keyword (here "mask")
            # is only a label; any name would work.
            with self.subTest(mask=mask):
                # Search only wflow_mask_dir, the one directory this test
                # checks.  The function raises ValueError if the directory
                # contains more than one file for the mask, and subTest()
                # records that as an error for this mask.  The list of files
                # it returns isn't needed: the mask names come from the files
                # in the directory, so each mask has at least one file there,
                # and the only question is whether it has more than one.
                find_all_files_for_single_vx_mask([str(wflow_mask_dir)], mask)

    def test_no_reserved_names(self):
        """No mask file in parm/metplus/vx_masks has a reserved name
        (see RESERVED_VX_MASK_NAME_REGEX).  Experiment generation checks this
        with MET's gen_vx_mask, which may not be available here."""
        wflow_mask_dir = TOP_DIR / "parm" / "metplus" / "vx_masks"
        files_with_reserved_names = sorted(
            path.name for path in wflow_mask_dir.iterdir()
            if path.suffix in VX_MASK_FILE_EXTENSIONS
            and RESERVED_VX_MASK_NAME_REGEX.match(path.stem))
        self.assertEqual(files_with_reserved_names, [])


if __name__ == "__main__":
    unittest.main()
