"""
The pio-installer command: the core's command line, with the PlatformIO target.

The target is chosen when the package is imported, before this runs.
"""

import sys

from .core.cli import main

__all__ = ["main"]

if __name__ == "__main__":
    sys.exit(main())
