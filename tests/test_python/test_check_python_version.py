""" Defines unit tests for check_python_version() in
ush/python_utils/check_python_version.py """

import importlib
import logging
import re
import types
import unittest
from unittest import mock

# The tests below need the module check_python_version.py itself, not just
# the function of the same name in it, for two things:
#
# - To read MIN_PYTHON_VERSION, which the module defines.
#
# - To test versions other than the running one.  check_python_version() reads
#   the version from sys.version_info.  The sys module is loaded once per run,
#   and each module that does "import sys", including check_python_version.py,
#   gets its own variable named sys, in its own namespace, that refers to that
#   one sys module object.  The tests use mock.patch.object() to temporarily
#   point the variable sys in check_python_version.py to a fake object with a
#   chosen version_info.  This changes only what that one variable refers to:
#   the real sys module is not changed, and the sys variables in all other
#   modules (e.g. unittest and logging) still refer to it.
#
# The usual ways of importing a module object don't work here, because
# python_utils/__init__.py does
#
#   from .check_python_version import check_python_version
#
# which makes the package attribute python_utils.check_python_version the
# function instead of the module.  Both
#
#   import python_utils.check_python_version as cpv_module
#   from python_utils import check_python_version as cpv_module
#
# look up that attribute and so return the function.  (A form like
# "from python_utils.check_python_version import MIN_PYTHON_VERSION" does
# work, because it gets the module from sys.modules, but it imports only
# names from inside the module, not the module object.)
# importlib.import_module() also gets the module from sys.modules, so it
# returns the module object.
cpv_module = importlib.import_module("python_utils.check_python_version")

# The minimum version, as (major, minor), and as a string, e.g. "3.10".
MIN_MAJOR, MIN_MINOR = cpv_module.MIN_PYTHON_VERSION
MIN_VERSION_STR = f"{MIN_MAJOR}.{MIN_MINOR}"


class Testing(unittest.TestCase):
    """ Class to run the tests. """

    def _check_with_version(self, version_info: tuple) -> None:
        """ Runs check_python_version() with sys.version_info in its module
        replaced by version_info, a tuple (major, minor, ...) of 2 or more
        integers like the start of sys.version_info.  Only the first 2 are
        used. """
        fake_sys = types.SimpleNamespace(version_info=version_info)
        with mock.patch.object(cpv_module, "sys", fake_sys):
            cpv_module.check_python_version()

    def test_current_version_passes(self) -> None:
        """ The Python version running the tests meets the minimum. """
        # Call check_python_version() directly, not through
        # _check_with_version() as the other tests do.  That's because this
        # test uses the real sys.version_info, so there is no version to fake.
        # This also tests the function the way the workflow's scripts call it.
        cpv_module.check_python_version()

    def test_minimum_version_passes(self) -> None:
        """ The minimum version itself (MIN_PYTHON_VERSION) passes. """
        self._check_with_version((MIN_MAJOR, MIN_MINOR, 0))

    def test_later_versions_pass(self) -> None:
        """ Later versions pass: a later minor version, and the next major
        version with minor version 0 (which is below the minimum's minor
        version, unless that is 0). """
        for version_info in [(MIN_MAJOR, MIN_MINOR + 4, 2), (MIN_MAJOR + 1, 0, 0)]:
            with self.subTest(version_info=version_info):
                self._check_with_version(version_info)

    def test_old_version_fails(self) -> None:
        """ A version just below MIN_PYTHON_VERSION raises an exception that
        names the minimum version. """
        # A version just below the minimum: the previous minor version, or,
        # if the minimum's minor version is 0, a late minor version of the
        # previous major version.
        if MIN_MINOR > 0:
            old_version_info = (MIN_MAJOR, MIN_MINOR - 1, 18)
        else:
            old_version_info = (MIN_MAJOR - 1, 99, 0)

        # check_python_version() logs an error message before raising its
        # exception.  That message would be printed in the middle of the test
        # output, where it would look like a real error although the test
        # passes, so turn logging off for this test:
        #
        # - logging.disable(level) turns off all log messages at level and
        #   below, for every logger in the process.  CRITICAL is the highest
        #   standard level, so this turns off all logging.
        #
        # - Because that affects the whole process, including the tests that
        #   run after this one, logging must be turned back on afterward.
        #   addCleanup() records a function and its arguments, and unittest
        #   calls it after the test finishes, whether the test passes, fails
        #   or raises an error.  Here it calls logging.disable(logging.NOTSET),
        #   which turns logging back on.
        #
        # Note that a plain call of the form
        #
        #   logging.disable(logging.NOTSET)
        #
        # after the "with" block below would be skipped if the assertion in
        # the "with" block failed.  That would in turn keep logging disabled
        # for all tests following the current one.
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        with self.assertRaisesRegex(
            Exception, f"Python version below {re.escape(MIN_VERSION_STR)}"
        ):
            self._check_with_version(old_version_info)
