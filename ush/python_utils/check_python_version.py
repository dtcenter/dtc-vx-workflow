#!/usr/bin/env python3

import sys
import logging
from textwrap import dedent

# Minimum Python version (major, minor) that the workflow needs.
MIN_PYTHON_VERSION = (3, 10)


def check_python_version():
    """Checks that the Python version is at least MIN_PYTHON_VERSION and for
    presence of some non-standard packages (currently ``uwtools``)

    Raises:
        ImportError: If checked packages are missing.
        Exception: If the Python version is less than MIN_PYTHON_VERSION.
    """

    # Check for non-standard Python packages
    try:
        import uwtools
    except ImportError:
        logging.error(
            dedent(
                """
                Error: Missing Python package required by the vx workflow
                """
            )
        )
        raise

    # Check the Python version
    #
    # sys.version_info is a named tuple with 5 elements that describe the
    # version of Python being used.  (A named tuple is one whose elements
    # can be accessed either by index or by name; otherwise it behaves like a
    # plain tuple.)  For example, if the version is 3.15.0b2, then the
    # elements of sys.version_info are as follows:
    #
    #   sys.version_info[0] (or sys.version_info.major):
    #     The major version number, e.g. the "3" in 3.15.0b2.
    #
    #   sys.version_info[1] (or sys.version_info.minor):
    #     The minor version number, e.g. the "15" in 3.15.0b2.
    #
    #   sys.version_info[2] (or sys.version_info.micro):
    #     The micro version number, e.g. the "0" in 3.15.0b2.
    #
    #   sys.version_info[3] (or sys.version_info.releaselevel):
    #     The release level: 'alpha', 'beta', 'candidate' or 'final', e.g.
    #     'beta' for 3.15.0b2.
    #
    #   sys.version_info[4] (or sys.version_info.serial):
    #     The number of the pre-release, e.g. the "2" in 3.15.0b2.
    #
    # Here, only the .major and .minor elements are needed because we use
    # sys.version_info[:2] in the comparison below.  That is the plain
    # 2-element tuple
    #
    #   (sys.version_info.major, sys.version_info.minor)
    #
    # Tuples are compared element by element, from left to right.  Comparison
    # of the first elements decides which tuple is larger unless they are
    # equal, in which case the second elements decide, and so on.  Each
    # element is compared as a whole number, so (3, 10) > (3, 9), i.e. version
    # 3.10 comes after 3.9 (unlike the decimal numbers 3.10 and 3.9, or the
    # strings "3.10" and "3.9"), and (4, 0) > (3, 10).
    if sys.version_info[:2] < MIN_PYTHON_VERSION:
        min_version = ".".join(str(n) for n in MIN_PYTHON_VERSION)
        version = ".".join(str(n) for n in sys.version_info[:2])
        logging.error(
            dedent(
                f"""
                Error: Python version must be {min_version} or higher
                Your Python version is: {version}"""
            )
        )
        raise Exception(f"Python version below {min_version}")


if __name__ == "__main__":
    try:
        check_python_version()
    except:
        logging.exception(
            dedent(
                """
                *************************************************************************
                FATAL ERROR:
                The system does not meet minimum requirements for running the vx workflow.
                *************************************************************************\n
                """
            )
        )
        sys.exit(1)
