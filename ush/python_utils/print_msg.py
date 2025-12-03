#!/usr/bin/env python3

import traceback
import sys
from textwrap import dedent, indent
from logging import getLogger


def print_err_msg_exit(error_msg="", stack_trace=True):
    """Prints out an error message to standard error and exits.
    It can optionally print the stack trace as well.

    Args:
        error_msg    (str): Error message to print
        stack_trace (bool): Set to ``True`` to print stack trace
    """
    if stack_trace:
        traceback.print_stack(file=sys.stderr)

    msg_footer = "\nExiting with nonzero status."
    print("FATAL ERROR: " + dedent(error_msg) + msg_footer, file=sys.stderr)
    sys.exit(1)

