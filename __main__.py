#!/usr/bin/env python3
"""
Main entry point for the Excel Processing System when run as a package.
"""

import sys
import os

# Add the parent directory to sys.path to allow running directly from source
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from the script file
from excel_processor import main as excel_processor_main


def main():
    """
    Main entry point when run as a package.
    """
    return excel_processor_main()


if __name__ == "__main__":
    sys.exit(main())