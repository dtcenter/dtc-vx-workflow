"""
Common logging functions for all python scripts in scripts/ directory
"""
import logging
import sys

def setup_logging(debug=False):
    
    """Calls initialization functions for logging package, and sets the
    user-defined level for logging in the script."""
    
    logger = logging.getLogger(__name__)
    if debug:
        print("Setting logging to DEBUG")
        level=logging.DEBUG
    else:
        print("Setting logging to INFO")
        level=logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
