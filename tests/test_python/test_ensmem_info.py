"""
Unit tests for get_ensmem_info() and EnsmemInfo.get_fn_template_vars() in
python_utils/ensmem_info.py.

To run them, issue the following command from the top-level directory:
    UNIT_TEST=True PYTHONPATH=ush python3 -m unittest -b tests/test_python/test_ensmem_info.py
"""

import unittest

from python_utils import EnsmemInfo, get_ensmem_info


def _make_cfg(indx_min, time_lags_hrs, fn_templates, ndigits=3):
    """Returns a minimal experiment configuration containing the settings used
    by get_ensmem_info(), in the form they have after setup.py has processed
    them (i.e. with FCST_FN_TEMPLATE expanded to one entry per member)."""
    nummems = len(time_lags_hrs)
    return {
        "ensemble": {
            "NUM_ENS_MEMBERS": nummems,
            "ENSMEM_INDX_MIN": indx_min,
            "ENSMEM_INDX_MAX": indx_min + nummems - 1,
            "ENS_TIME_LAG_HRS": time_lags_hrs,
        },
        "verification": {
            "VX_NDIGITS_ENSMEM_NAMES": ndigits,
            "FCST_FN_TEMPLATE": fn_templates,
        },
    }


class TestGetEnsmemInfo(unittest.TestCase):
    """Tests for get_ensmem_info()."""

    def test_ensemble(self):
        """Index (as an integer and as a zero-padded string), position, name,
        time lag, and template of each member of an ensemble, for
        ENSMEM_INDX_MIN = 0 and 1 and for 2- and 3-digit indices.  The template
        is returned as is, i.e. with any ${...} variables in it left
        unsubstituted."""
        fn_templates = [
            "${ensmem_name}/fcst_a.f{lead?fmt=%HHH?shift=${time_lag}}.grib2",
            "${ensmem_name}/fcst_b.f{lead?fmt=%HHH?shift=${time_lag}}.grib2",
            "${ensmem_name}/fcst_c.f{lead?fmt=%HHH?shift=${time_lag}}.grib2",
        ]
        time_lags_hrs = [0, 6, 12]
        cases = [
            (0, 3, ["000", "001", "002"]),
            (1, 3, ["001", "002", "003"]),
            (1, 2, ["01", "02", "03"]),
        ]
        for indx_min, ndigits, index_strs in cases:
            cfg = _make_cfg(indx_min, time_lags_hrs, fn_templates, ndigits)
            for pos, index_str in enumerate(index_strs):
                with self.subTest(indx_min=indx_min, ndigits=ndigits, pos=pos):
                    self.assertEqual(
                        get_ensmem_info(cfg, indx_min + pos),
                        EnsmemInfo(
                            index=indx_min + pos,
                            index_str=index_str,
                            pos=pos,
                            name=f"mem{index_str}",
                            time_lag=time_lags_hrs[pos] * 3600,
                            fcst_fn_template=fn_templates[pos],
                        ),
                    )

    def test_deterministic(self):
        """A deterministic forecast is a single member with index
        ENSMEM_INDX_MIN."""
        cfg = _make_cfg(0, [3], ["fcst.grib2"])
        self.assertEqual(
            get_ensmem_info(cfg, 0),
            EnsmemInfo(index=0, index_str="000", pos=0, name="mem000",
                       time_lag=10800, fcst_fn_template="fcst.grib2"),
        )

    def test_index_out_of_range(self):
        """An index outside of [ENSMEM_INDX_MIN, ENSMEM_INDX_MAX] raises a
        ValueError."""
        cfg = _make_cfg(1, [0, 0, 0], ["a", "b", "c"])
        for ensmem_index in (0, 4):
            with self.subTest(ensmem_index=ensmem_index):
                with self.assertRaises(ValueError):
                    get_ensmem_info(cfg, ensmem_index)


class TestGetFnTemplateVars(unittest.TestCase):
    """Tests for EnsmemInfo.get_fn_template_vars()."""

    def setUp(self):
        cfg = _make_cfg(1, [0, 6], ["a", "b"])
        self.ensmem_info = get_ensmem_info(cfg, 2)

    def test_get_fn_template_vars(self):
        """The member's name, zero-padded index, and time lag (in seconds)."""
        self.assertEqual(
            self.ensmem_info.get_fn_template_vars(),
            {"ensmem_name": "mem002", "ensmem_indx": "002", "time_lag": 21600},
        )

    def test_get_fn_template_vars_no_time_lag(self):
        """With apply_time_lag=False, the time lag is 0."""
        self.assertEqual(
            self.ensmem_info.get_fn_template_vars(apply_time_lag=False),
            {"ensmem_name": "mem002", "ensmem_indx": "002", "time_lag": 0},
        )


if __name__ == "__main__":
    unittest.main()
