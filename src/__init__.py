"""
Install embedded C and C++ libraries into a PlatformIO project.

Installed with pip, it is the pio-installer command. It takes a library from
GitHub, from a downloaded zip, or from a folder, puts it into the project's
lib folder with a library.json written for it, and gives the whole project
the defines it needs in platformio.ini. Every framework PlatformIO builds
with finds it there: Arduino, ESP-IDF, STM32Cube, Zephyr and the rest.

The work that is the same for any project is the shared core, in core/, from
github.com/nimaltd/core-installer. What a PlatformIO project is, is in pio.py.

See https://github.com/nimaltd/pio-installer
"""

__version__ = "1.0.0"

# Before anything of the core is used: it asks the target for every answer
# that depends on the kind of project.
from .core import target as _target  # noqa: E402
from .pio import PlatformIO  # noqa: E402

_target.use(PlatformIO(__version__))

from .core.installer import InstallError, Result, install_in_place, install_to  # noqa: E402
from .core.manifest import Manifest, ManifestError, load  # noqa: E402

__all__ = [
    "InstallError",
    "Manifest",
    "ManifestError",
    "Result",
    "install_in_place",
    "install_to",
    "load",
    "main",
]


def main(argv=None):
    """Run the command line interface. Imported lazily to keep start-up cheap."""
    from .cli import main as _main

    return _main(argv=argv)
