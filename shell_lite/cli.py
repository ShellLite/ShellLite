"""
-----Purpose: CLI entry point wrapper for the ShellLite compiler.
"""
import sys
import os

if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_dir)

from .main import main

if __name__ == "__main__":
    """
    -----Purpose: Main execution entry point.
    """
    main()