"""
What 2.0.0 brings to a PlatformIO project: its block on the shared helper,
recorded with its fingerprint, a half written one left alone rather than taking
the user's lines with it, and files of the project's own made once.
"""

import json

from conftest import read

from pio_installer import ini
from pio_installer.core import cli
from pio_installer.core.target import MANUAL


def _install(*args):
    return cli.main([str(arg) for arg in args])


def test_the_block_is_recorded_with_its_fingerprint(library, project, nobody, no_network):
    root = project()

    assert _install(library(defines=["DEMO_FAST"]), "--project", root) == 0

    record = json.loads(read(root / ".pio-installer.json"))["libraries"]["demo"]
    assert list(record["blocks"]["platformio.ini"]) == ["demo"]


def test_a_half_written_block_is_left_alone_with_the_lines_to_add(project, library, nobody, no_network, tmp_path):
    from pio_installer.core import manifest

    text = "[env:native]\nbuild_flags =\n    ; >>> pio-installer: demo >>>\n    -DOLD\n\nlib_deps = mine\n"
    root = project(ini=text)
    loaded = manifest.load(library(defines=["DEMO_FAST"]))

    outcome = ini.integrate(root, loaded)

    assert outcome.status == MANUAL
    assert outcome.steps[-1] == "-DDEMO_FAST"
    assert read(root / "platformio.ini") == text


def test_uninstall_leaves_a_half_written_block_alone(project, nobody):
    text = "[env:native]\nbuild_flags =\n    ; >>> pio-installer: demo >>>\n    -DOLD\nlib_deps = mine\n"
    root = project(ini=text)

    outcome = ini.uninstall(root, "demo")

    assert outcome.status == MANUAL
    assert read(root / "platformio.ini") == text


def test_once_files_land_in_the_project_and_never_in_platformio_ini(library, project, nobody, no_network, capsys):
    root = project()
    once = {"once": [{"from": "project/VERSION"}]}

    assert _install(library(requires={"pio_installer": "2.0.0"}, extra=once, files={"project/VERSION": "1\n"}),
                    "--project", root) == 0
    assert (root / "VERSION").read_text() == "1\n"

    bad = {"once": [{"from": "project/VERSION", "to": "platformio.ini"}]}
    assert _install(library(name="bad", requires={"pio_installer": "2.0.0"}, extra=bad,
                            files={"project/VERSION": "1\n"}, root=root.parent / "bad"),
                    "--project", root) == 2
    assert "edits or reads as the project's own" in capsys.readouterr().err
