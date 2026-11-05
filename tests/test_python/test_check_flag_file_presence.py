""" Defines unit tests for the check_flag_file_presence.sh script in the
ush directory """

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(TEST_DIR, "..", "..", "ush", "check_flag_file_presence.sh")
PATTERN = "get_obs_mrms_*_complete.txt"


class Testing(unittest.TestCase):
    """ Class to run the tests. """

    def setUp(self) -> None:
        self.flag_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.flag_dir)

    def _touch_flag_files(self, *days: str) -> None:
        for day in days:
            (self.flag_dir / PATTERN.replace("*", day)).touch()

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([SCRIPT, *args], capture_output=True, text=True, check=False)

    def test_all_flag_files_present(self) -> None:
        """ The check passes if there is a flag file for each obs day, including
        when the obs days are not consecutive and there are flag files for
        other days. """
        self._touch_flag_files("20240429", "20240430", "20240501")
        result = self._run(str(self.flag_dir), PATTERN, "20240429", "20240501")
        self.assertEqual(result.returncode, 0)

    def test_flag_file_missing(self) -> None:
        """ The check fails, listing the missing flag file, if there is no flag
        file for one of the obs days (even if there is one for a day in between). """
        self._touch_flag_files("20240429", "20240430")
        result = self._run(str(self.flag_dir), PATTERN, "20240429", "20240501")
        self.assertEqual(result.returncode, 1)
        self.assertIn(PATTERN.replace("*", "20240501"), result.stderr)
        self.assertNotIn(PATTERN.replace("*", "20240429"), result.stderr)

    def test_flag_files_dir_missing(self) -> None:
        """ The check fails if the flag files directory does not exist. """
        result = self._run(str(self.flag_dir / "nonexistent"), PATTERN, "20240429")
        self.assertEqual(result.returncode, 1)

    def test_flag_file_with_hour(self) -> None:
        """ The check fails for flag files containing the hour (YYYYMMDDHH)
        instead of just the day in place of the "*". """
        (self.flag_dir / "NDAS_nc_obs_2024042900_ready.txt").touch()
        result = self._run(str(self.flag_dir), "NDAS_nc_obs_*_ready.txt", "20240429")
        self.assertEqual(result.returncode, 1)

    def test_invalid_arguments(self) -> None:
        """ The script exits with status 2 if no obs days are given or if the
        pattern does not contain exactly one "*". """
        self.assertEqual(self._run(str(self.flag_dir), PATTERN).returncode, 2)
        for pattern in ["get_obs_mrms_complete.txt", "get_obs_*_*_complete.txt"]:
            with self.subTest(pattern=pattern):
                self.assertEqual(self._run(str(self.flag_dir), pattern, "20240429").returncode, 2)
