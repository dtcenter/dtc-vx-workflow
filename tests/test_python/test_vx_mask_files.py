"""
Unit tests for get_file_for_each_vx_mask() and
find_all_files_for_single_vx_mask() in python_utils/vx_mask_files.py, and a
check of the mask files that come with the workflow in parm/metplus/vx_masks.

To run them, issue the following command from the top-level directory:
    UNIT_TEST=True PYTHONPATH=ush python3 -m unittest -b tests/test_python/test_vx_mask_files.py
"""

import os
import tempfile
import unittest
from pathlib import Path

from python_utils import (
    find_all_files_for_single_vx_mask, get_file_for_each_vx_mask, get_vx_mask_dirs
)
from python_utils.vx_mask_files import VX_MASK_FILE_EXTENSIONS

TOP_DIR = Path(__file__).resolve().parents[2]


class TestVxMaskFiles(unittest.TestCase):
    """Tests for get_file_for_each_vx_mask() and find_all_files_for_single_vx_mask()."""

    # unittest calls setUp() automatically before each test method (each method
    # whose name starts with "test"), so each test starts with its own new,
    # empty set of directories.  The cleanup that setUp() registers with
    # addCleanup() deletes them automatically after the test, whether it
    # passes or fails.
    def setUp(self):
        """Creates, in a temporary directory, the three directories that are
        searched: a user mask directory (VX_MASK_DIR), a parm directory
        (PARMdir) containing metplus/vx_masks, and a MET installation
        (MET_INSTALL_DIR) containing share/met/poly."""
        # pylint: disable=consider-using-with
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.user_dir = os.path.join(tmp_dir.name, "user_masks")
        self.parm_dir = os.path.join(tmp_dir.name, "parm")
        self.wflow_mask_dir = os.path.join(self.parm_dir, "metplus", "vx_masks")
        self.met_install_dir = os.path.join(tmp_dir.name, "met")
        self.met_poly_dir = os.path.join(self.met_install_dir, "share", "met", "poly")
        for d in (self.user_dir, self.wflow_mask_dir, self.met_poly_dir):
            os.makedirs(d)

    def _make_cfg(self, vx_masks, vx_mask_dir=None):
        """Returns a minimal experiment configuration containing the settings
        used by get_file_for_each_vx_mask().  VX_MASK_DIR is set to the user
        mask directory unless vx_mask_dir is given ("" for unset)."""
        return {
            "verification": {
                "VX_MASKS": vx_masks,
                "VX_MASK_DIR": self.user_dir if vx_mask_dir is None else vx_mask_dir,
            },
            "user": {"PARMdir": self.parm_dir},
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


if __name__ == "__main__":
    unittest.main()
