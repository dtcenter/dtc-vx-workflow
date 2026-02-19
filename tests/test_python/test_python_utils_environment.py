"""Tests all functions in ush/python_utils/environment.py"""
#pylint: disable=missing-function-docstring
import os
import unittest
from datetime import datetime

# Import the target module
from python_utils import (
    str_to_date,
    date_to_str,
    str_to_type,
    type_to_str,
    list_to_str,
    str_to_list,
    set_env_var,
    get_env_var,
    import_vars,
    export_vars,
)


class TestEnvironmentFunctions(unittest.TestCase):
    """Unit tests for every public function in python_utils.environment."""

    # ------------------------------------------------------------------ #
    # 1. str_to_date ----------------------------------------------------- #
    # ------------------------------------------------------------------ #
    def test_str_to_date_valid(self):
        # 8‑digit
        self.assertEqual(str_to_date("20220101"), datetime(2022, 1, 1))
        # 10‑digit
        self.assertEqual(str_to_date("2022010112"), datetime(2022, 1, 1, 12))
        # 12‑digit
        self.assertEqual(str_to_date("202201011230"), datetime(2022, 1, 1, 12, 30))
        # 14‑digit
        self.assertEqual(
            str_to_date("20220101123045"), datetime(2022, 1, 1, 12, 30, 45)
        )

    def test_str_to_date_invalid(self):
        for bad in ["", "2022", "20220101123", "2022010112304", "abcd", None]:
            self.assertIsNone(str_to_date(bad))

    # ------------------------------------------------------------------ #
    # 2. date_to_str ----------------------------------------------------- #
    # ------------------------------------------------------------------ #
    def test_date_to_str_default(self):
        dt = datetime(2022, 1, 1, 12, 30, 45)
        self.assertEqual(date_to_str(dt), "202201011230")

    def test_date_to_str_custom(self):
        dt = datetime(2022, 1, 1, 12, 30, 45)
        self.assertEqual(date_to_str(dt, "%Y-%m-%d %H:%M:%S"), "2022-01-01 12:30:45")

    # ------------------------------------------------------------------ #
    # 3. str_to_type ----------------------------------------------------- #
    # ------------------------------------------------------------------ #
    def test_str_to_type_basic(self):
        self.assertTrue(str_to_type("True"))
        self.assertFalse(str_to_type("false"))
        self.assertEqual(str_to_type("None"), None)
        self.assertEqual(str_to_type("spam"), "spam")

    def test_str_to_type_numbers(self):
        self.assertEqual(str_to_type("123"), 123)
        self.assertEqual(str_to_type("0123"), "0123")  # leading 0 preserved
        self.assertAlmostEqual(str_to_type("3.14"), 3.14)

    def test_str_to_type_datetime(self):
        # 8 digits -> datetime
        self.assertIsInstance(str_to_type("20220101", return_string=0), datetime)
        # 10 digits
        self.assertIsInstance(str_to_type("2022010112"), datetime)
        # 12 digits
        self.assertIsInstance(str_to_type("202201011230"), datetime)
        # 14 digits
        self.assertIsInstance(str_to_type("20220101123045"), datetime)

    def test_str_to_type_return_string(self):
        self.assertEqual(str_to_type("123", return_string=1), "123")

    # ------------------------------------------------------------------ #
    # 4. type_to_str ----------------------------------------------------- #
    # ------------------------------------------------------------------ #
    def test_type_to_str(self):
        self.assertEqual(type_to_str(True), "True")
        self.assertEqual(type_to_str(42), "42")
        self.assertEqual(type_to_str(3.14), "3.14")
        self.assertEqual(type_to_str(datetime(2022, 1, 1)), "202201010000")
        self.assertEqual(type_to_str(None), "")
        self.assertEqual(type_to_str("spam"), "spam")

    # ------------------------------------------------------------------ #
    # 5. list_to_str ----------------------------------------------------- #
    # ------------------------------------------------------------------ #
    def test_list_to_str_oneline(self):
        self.assertEqual(
            list_to_str([1, 2, "three"]), '( "1" "2" "three" )'
        )
        self.assertEqual(
            list_to_str(["a", "b"]), '( "a" "b" )'
        )

    def test_list_to_str_multiline(self):
        long = ["a"] * 7
        # >4 items, multiline
        expected = "( \\\n\"a\" \\\n\"a\" \\\n\"a\" \\\n\"a\" \\\n\"a\" \\\n\"a\" \\\n\"a\" \\\n)"
        self.assertEqual(list_to_str(long), expected)

    def test_list_to_str_nonlist(self):
        self.assertEqual(list_to_str("spam"), "spam")

    # ------------------------------------------------------------------ #
    # 6. str_to_list ----------------------------------------------------- #
    # ------------------------------------------------------------------ #
    def test_str_to_list_brackets(self):
        self.assertEqual(
            str_to_list("( \"1\" \"2\" \"3\" )"),
            [1, 2, 3],
        )
        self.assertEqual(
            str_to_list("[ \"a\" \"b\" ]"), ["a", "b"]
        )

    def test_str_to_list_without_brackets(self):
        self.assertEqual(str_to_list("spam"), "spam")

    def test_str_to_list_empty(self):
        self.assertEqual(str_to_list("( )"), [])
        self.assertIsNone(str_to_list("()"), [])
        self.assertIsNone(str_to_list(""))

    # ------------------------------------------------------------------ #
    # 7. set_env_var / get_env_var ------------------------------------- #
    # ------------------------------------------------------------------ #
    def test_set_and_get_env_var(self):
        set_env_var("TEST_VAR", ["one", "two"])
        self.assertEqual(
            os.getenv("TEST_VAR"), '( "one" "two" )'
        )
        self.assertEqual(
            get_env_var("TEST_VAR"), ["one", "two"]
        )

    # ------------------------------------------------------------------ #
    # 8. import_vars / export_vars ------------------------------------- #
    # ------------------------------------------------------------------ #
    def test_import_and_export_vars(self):
        #pylint: disable=global-variable-undefined
        # Set some globals
        global TEST_GLOBAL
        TEST_GLOBAL = "hello"

        # Export to env
        export_vars()
        self.assertEqual(os.getenv("TEST_GLOBAL"), "hello")

        # Clear env, set via env
        os.environ["TEST_GLOBAL"] = "world"
        # Import into module globals
        import_vars()
        self.assertEqual(TEST_GLOBAL, "world")

    def test_import_vars_specific(self):
        os.environ["VAR1"] = "1"
        os.environ["VAR2"] = "2"
        import_vars(env_vars=["VAR1"])
        self.assertEqual(VAR1, 1)
        with self.assertRaises(NameError):
            _ = VAR2  # not imported

    def test_export_vars_specific(self):
        #pylint: disable=global-variable-undefined
        global VAR1, VAR2
        VAR1 = "x"
        VAR2 = "y"
        export_vars(env_vars=["VAR1"])
        self.assertEqual(os.getenv("VAR1"), "x")
        self.assertIsNone(os.getenv("VAR2"))


if __name__ == "__main__":
    unittest.main()
