"""
Unit tests for find_duplicate_yaml_keys() in python_utils/yaml_duplicate_keys.py.

To run them, set PYTHONPATH=ush in the environment, and issue the following command from the
top-level directory:
    python3 -m unittest -b tests/test_python/test_yaml_duplicate_keys.py
"""

import subprocess
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

from python_utils import find_duplicate_yaml_keys

TOP_DIR = Path(__file__).resolve().parents[2]
#
# YAML files in the repository that contain duplicate keys and are therefore
# not checked by test_repo_yaml_files(), each with the reason it is allowed.
#
FILES_WITH_KNOWN_DUPLICATES = {
    # An example of the files written by monitor_jobs.py, with one entry per
    # job status, all for the same experiment.  It is not read by any code.
    "tests/WE2E/WE2E_tests.yaml",
}


class TestFindDuplicateKeys(unittest.TestCase):
    """Tests for find_duplicate_yaml_keys()."""

    def setUp(self):
        # pylint: disable=consider-using-with
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def _find(self, contents):
        """Write contents to a YAML file and return find_duplicate_yaml_keys() for it."""
        yaml_path = Path(self.tmp_dir.name) / "config.yaml"
        yaml_path.write_text(dedent(contents), encoding="utf-8")
        return find_duplicate_yaml_keys(yaml_path)

    def test_config_without_duplicates(self):
        """No duplicates, with tags (which are not evaluated), anchors and aliases, merge keys,
        and the same key in different mappings."""
        self.assertEqual(
            self._find(
                """\
                workflow:
                  NPROCS: !int '{{ 2 * 2 }}'
                  LAGS: !list '[ 0, 6 ]'
                defaults: &defaults
                  execution: {walltime: 01:00:00}
                extra: &extra
                  NPROCS: 2
                gridstat:
                  <<: *defaults
                  <<: *extra
                pointstat:
                  execution: {walltime: 02:00:00}
                """
            ),
            [],
        )

    def test_config_with_duplicates(self):
        """Duplicate keys at the top level and in nested mappings, in the order in which the
        keys first appear, with all the lines on which each one appears."""
        self.assertEqual(
            self._find(
                """\
                workflow:
                  PREEXISTING_DIR_METHOD: rename
                  FCST_LEN_HRS: 6
                genensprod:
                  execution:
                    memory: 120G
                workflow:
                  PREEXISTING_DIR_METHOD: quit
                  PREEXISTING_DIR_METHOD: delete
                genensprod:
                  NPROCS: 4
                """
            ),
            [
                "workflow (lines 1, 7)",
                "genensprod (lines 4, 10)",
                "workflow.PREEXISTING_DIR_METHOD (lines 8, 9)",
            ],
        )

    def test_duplicate_in_sequence(self):
        """A duplicate key in a mapping that is an item of a sequence."""
        self.assertEqual(
            self._find(
                """\
                fields:
                  - name: TMP
                    level: Z2
                    level: Z10
                """
            ),
            ["fields[0].level (lines 3, 4)"],
        )

    def test_empty_file(self):
        """An empty file has no duplicate keys."""
        self.assertEqual(self._find(""), [])

    def test_repo_yaml_files(self):
        """None of the YAML files tracked by git in the repository have duplicate keys, except
        those in FILES_WITH_KNOWN_DUPLICATES."""
        #
        # Get the list of files from git rather than by searching the directory
        # tree, so that a file added anywhere in the repository is checked as
        # soon as it is committed, while files that are not part of the
        # repository (e.g. a conda installation under the top-level directory,
        # or a user's own config files) are not.
        #
        try:
            result = subprocess.run(
                ["git", "ls-files", "*.yaml", "*.yml"],
                cwd=TOP_DIR,
                capture_output=True,
                text=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git ls-files failed (git not available or not a git repository)")
        yaml_paths = [
            path
            for path in result.stdout.splitlines()
            if path not in FILES_WITH_KNOWN_DUPLICATES
        ]
        self.assertNotEqual(yaml_paths, [], "git ls-files found no YAML files")
        for yaml_path in yaml_paths:
            with self.subTest(yaml_path=yaml_path):
                self.assertEqual(find_duplicate_yaml_keys(TOP_DIR / yaml_path), [])


if __name__ == "__main__":
    unittest.main()
