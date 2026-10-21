"""Loads the package from src under its own name, before any test imports it."""

import importlib.util
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

if "pio_installer" not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        "pio_installer", SRC / "__init__.py", submodule_search_locations=[str(SRC)]
    )
    _package = importlib.util.module_from_spec(_spec)
    sys.modules["pio_installer"] = _package
    _spec.loader.exec_module(_package)
