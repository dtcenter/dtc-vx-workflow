#!/usr/bin/env python3

"""
Python Script Documentation Block

 Script name:       	exregional_integration_test.py
 Script description:  	Ensures the correct number of netcdf files are generated
 			for each experiment

 Author:  Eddie Snyder 	Org: NOAA EPIC		Date: 2024-02-05

 Notes/future work:    - Currently SRW App only accepts netcdf as the UFS WM
                         output file format. If that changes, then additional
                         logic is needed to address the other file formats.
                       - SRW App doesn't have a variable that updates the
                         forecast increment. The UFS WM does with the
                         output_fh variable, which can be found in the
                         model_configure file. If it becomes available with
                         the SRW App, then logic is needed to account for the
                         forecast increment variable.

"""

import abc
import argparse
import itertools
import logging
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

from uwtools.api.config import get_nml_config
from uwtools.config.formats.nml import NMLConfig

logging.basicConfig(format="[%(name)s][%(levelname)s] %(message)s", level=logging.INFO)
LOGGER = logging.getLogger("task_integration_test")


@dataclass
class ContextForTest:
    fcst_dir: Path
    fcst_len: int
    fcst_inc: int


class AbstractIntegrationTest(abc.ABC, unittest.TestCase):
    _ctx: ContextForTest | None = None

    @classmethod
    def get_context(cls) -> ContextForTest:
        if cls._ctx is None:
            raise ValueError
        return cls._ctx

    @classmethod
    def set_context(cls, ctx: ContextForTest) -> None:
        cls._ctx = ctx


class TestExptFiles(AbstractIntegrationTest):
    """
    Set up the test for expected output files.
    """

    def test_fcst_files(self) -> None:
        """
        Test that expected files exist.
        """

        ctx = self.get_context()

        # Check if model_configure exists
        model_configure_fp = ctx.fcst_dir / "model_configure"
        self.assertTrue(model_configure_fp.exists())

        # Loop through model_configure file to find the netcdf base names
        with open(model_configure_fp, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("filename_base"):
                    filename_base_1 = line.split("'")[1]
                    filename_base_2 = line.split("'")[3]
                    break

        # Create list of expected filenames from the experiment
        filename_list = []

        for x in range(0, args.fcst_len + 1, args.fcst_inc):
            fhour = str(x).zfill(3)
            filename_1 = f"{filename_base_1}f{fhour}.nc"
            filename_2 = f"{filename_base_2}f{fhour}.nc"
            filename_list.append(filename_1)
            filename_list.append(filename_2)

        # Confirm that filenames exist
        for filename in filename_list:
            filename_fp = ctx.fcst_dir / filename
            LOGGER.info(f"Checking existence of: {str(filename_fp)}")
            err_msg = f"Missing file: {str(filename_fp)}"
            self.assertTrue(filename_fp.exists(), err_msg)


# -------------Start of script -------------------------#
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fcst_dir",
        help="Directory to forecast files.",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--fcst_len",
        help="Forecast length.",
        required=True,
        type=int,
    )
    parser.add_argument(
        "--fcst_inc",
        default=1,
        help="Increment of forecast in hours.",
        required=False,
        type=int,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug messages.",
        required=False,
    )
    parser.add_argument("unittest_args", nargs="*")
    args = parser.parse_args()
    sys.argv[1:] = args.unittest_args

    if args.debug:
        LOGGER.setLevel(logging.DEBUG)
        LOGGER.debug("logging level set to DEBUG")
    LOGGER.info(f"{args=}")

    config = ContextForTest(
        fcst_dir=args.fcst_dir, fcst_len=args.fcst_len, fcst_inc=args.fcst_inc
    )
    LOGGER.info(f"{config=}")

    # Call unittest class
    TestExptFiles.set_context(config)
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestExptFiles))

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
