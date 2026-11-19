"""
Unit tests for find_unknown_config_keys() in python_utils/unknown_config_keys.py and for
check_for_unknown_keys() in setup.py.

To run them, set PYTHONPATH=ush in the environment, and issue the following command from the
top-level directory:
    python3 -m unittest -b tests/test_python/test_unknown_config_keys.py
"""

import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

from uwtools.api.config import get_yaml_config

from python_utils import find_unknown_config_keys
from python_utils.parse_test_list import ALL_TESTS
from setup import check_for_unknown_keys

TOP_DIR = Path(__file__).resolve().parents[2]
USH_DIR = TOP_DIR / "ush"
WE2E_DIR = TOP_DIR / "tests" / "WE2E"

REF_CONFIG = {
    "workflow": {"FCST_LEN_HRS": 6, "taskgroups": ["parm/wflow/verify_det.yaml"]},
    "verification": {"VX_FIELD_GROUPS": ["APCP"]},
    "genensprod": {
        "execution": {"walltime": "02:00:00"},
        "conf": {"LOG_GEN_ENS_PROD_VERBOSITY": 2},
        "fields": {},
    },
    "gridstat": {"execution": {"walltime": "01:00:00"}, "NPROCS": 1},
}


class TestFindUnknownKeys(unittest.TestCase):
    """Tests for find_unknown_config_keys()."""

    def test_no_unknown_keys(self):
        """A config whose keys are all in the reference, including a partial one."""
        config = {
            "workflow": {"FCST_LEN_HRS": 12},
            "genensprod": {"execution": {"walltime": "08:00:00"}},
        }
        self.assertEqual(find_unknown_config_keys(config, REF_CONFIG), [])

    def test_unknown_keys(self):
        """Misspelled and misplaced keys at several levels, in the order in which they appear,
        with only the topmost unknown key of each subtree reported."""
        config = {
            "verification": {"VX_FIELD_GROUP": ["SFC"]},
            "ensemble": {"execution": {"walltime": "08:00:00", "memory": "120G"}},
            "genensprod": {"execution": {"walltime": "08:00:00", "memroy": "120G"}},
        }
        self.assertEqual(
            find_unknown_config_keys(config, REF_CONFIG),
            ["verification.VX_FIELD_GROUP", "ensemble", "genensprod.execution.memroy"],
        )

    def test_free_form_paths(self):
        """Keys at a free-form path are accepted, with everything under them, even though the
        reference doesn't define them."""
        config = {
            "rocoto": {"tasks": {"task_anything": {"walltime": "00:10:00"}}},
            "workflow": {"FREE_FORM": {"anything": 1}, "CYCL_FREQ": 6},
        }
        self.assertEqual(
            find_unknown_config_keys(
                config, REF_CONFIG, free_form_paths=["rocoto", "workflow.FREE_FORM"]
            ),
            ["workflow.CYCL_FREQ"],
        )

    def test_free_form_keys(self):
        """The contents of a free-form key are not compared where the reference defines the key,
        but the key is unknown where the reference doesn't define it."""
        config = {
            "genensprod": {
                "conf": {"GEN_ENS_PROD_EAS_PROB_SHAPE": "CIRCLE"},
                "fields": {"SFC": [{"fcst_name": "TMP"}]},
            },
            "gridstat": {"conf": {"GRID_STAT_NC_PAIRS_FLAG_LATLON": False}},
        }
        self.assertEqual(
            find_unknown_config_keys(config, REF_CONFIG, free_form_keys=["conf", "fields"]),
            ["gridstat.conf"],
        )

    def test_values_not_dicts_in_both(self):
        """Lists are not compared item by item, and the contents of a value that is a dict in only
        one of the two configs are not compared."""
        config = {
            "workflow": {
                "taskgroups": ["parm/wflow/verify_ens.yaml", {"anything": 1}],
                "FCST_LEN_HRS": {"anything": 1},
            },
            "gridstat": {"execution": None},
        }
        self.assertEqual(find_unknown_config_keys(config, REF_CONFIG), [])


class TestCheckForUnknownKeys(unittest.TestCase):
    """Tests for check_for_unknown_keys() in setup.py."""

    def setUp(self):
        # pylint: disable=consider-using-with
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def test_error_message(self):
        """The error lists each unknown key, and the free-form paths and keys of the workflow are
        accepted."""
        user_config_path = Path(self.tmp_dir.name) / "config.yaml"
        user_config_path.write_text(
            dedent(
                """\
                user:
                  MACHINE: hera
                verification:
                  VX_FIELD_GROUP: [ "SFC" ]
                ensemble:
                  execution:
                    walltime: 08:00:00
                genensprod:
                  conf:
                    GEN_ENS_PROD_EAS_PROB_SHAPE: 'CIRCLE'
                gridstat:
                  fields:
                    SFC:
                      - fcst_name: TMP
                rocoto:
                  tasks:
                    task_anything:
                      walltime: 00:10:00
                """
            ),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError) as context:
            check_for_unknown_keys(
                user_config_path,
                USH_DIR / "config_defaults.yaml",
                USH_DIR / "machine" / "hera.yaml",
            )
        listed = [
            line.strip() for line in str(context.exception).splitlines() if line.startswith("  ")
        ]
        self.assertEqual(listed, ["verification.VX_FIELD_GROUP", "ensemble.execution"])

    def test_machine_file_keys(self):
        """A key defined only in a machine file (platform.FIXgsm, in linux.yaml) is accepted if
        that is the user's machine (linux) and rejected otherwise (hera)."""
        user_config_path = Path(self.tmp_dir.name) / "config.yaml"
        user_config_path.write_text(
            "platform:\n  FIXgsm: /path/to/fix_am\n", encoding="utf-8"
        )
        check_for_unknown_keys(
            user_config_path, USH_DIR / "config_defaults.yaml", USH_DIR / "machine" / "linux.yaml"
        )
        with self.assertRaises(ValueError):
            check_for_unknown_keys(
                user_config_path,
                USH_DIR / "config_defaults.yaml",
                USH_DIR / "machine" / "hera.yaml",
            )

    def test_repo_user_configs(self):
        """None of the user configs in the repository (the WE2E test configs and the configs in
        ush/configs) contain keys that are not workflow settings.  Each is checked with the
        machine file of the machine it sets (linux if it doesn't set one, as for the WE2E test
        configs in test_generate_wflow.py)."""
        config_paths = [WE2E_DIR / test for test in ALL_TESTS] + sorted(
            (USH_DIR / "configs").rglob("*.yaml")
        )
        self.assertNotEqual(config_paths, [])
        for config_path in config_paths:
            with self.subTest(config=str(config_path.relative_to(TOP_DIR))):
                user = get_yaml_config(config_path).data.get("user") or {}
                machine = (user.get("MACHINE") or "linux").lower()
                check_for_unknown_keys(
                    config_path,
                    USH_DIR / "config_defaults.yaml",
                    USH_DIR / "machine" / f"{machine}.yaml",
                )


if __name__ == "__main__":
    unittest.main()
