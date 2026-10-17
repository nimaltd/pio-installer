"""
Taking a library out of a PlatformIO project.

Installed and then uninstalled, platformio.ini is back to the byte it was, and
the library's folder, library.json included, is gone.
"""

import pytest
from conftest import read

from pio_installer.core import cli


def _install(*args):
    assert cli.main([str(arg) for arg in args]) == 0


def _uninstall(*args):
    return cli.main(["--uninstall"] + [str(arg) for arg in args])


@pytest.mark.parametrize("crlf", [False, True])
@pytest.mark.parametrize("ini", [
    "[env:native]\nplatform = native\n",
    "[env]\nbuild_flags = -DC\n\n[env:a]\nplatform = native\n\n[env:b]\nbuild_flags =\n    -DB\n",
])
def test_the_project_is_back_as_it_was(library, project, nobody, no_network, crlf, ini, capsys):
    root = project(ini=ini, crlf=crlf)
    before = read(root / "platformio.ini")
    _install(library(defines=["DEMO_FAST", "DEMO_N=2"]), "--project", root)
    assert read(root / "platformio.ini") != before

    assert _uninstall("demo", "--project", root) == 0

    assert read(root / "platformio.ini") == before
    assert not (root / "lib" / "demo").exists()
    assert "Removed demo's defines from platformio.ini." in capsys.readouterr().out


def test_a_librarys_own_library_json_goes_with_its_files(library, project, nobody, no_network):
    root = project()
    _install(library(extra={"extras": ["library.json"]}, files={"library.json": '{"name": "demo"}\n'}),
             "--project", root)

    assert _uninstall("demo", "--project", root) == 0

    assert not (root / "lib" / "demo").exists()


def test_one_of_two_libraries_comes_out(library, project, nobody, no_network, tmp_path):
    root = project()
    _install(library(name="two", defines=["TWO"], root=tmp_path / "repos" / "two"), "--project", root)
    only_two = read(root / "platformio.ini")
    _install(library(defines=["ONE"]), "--project", root)

    assert _uninstall("demo", "--project", root) == 0

    assert read(root / "platformio.ini") == only_two
    assert (root / "lib" / "two" / "library.json").is_file()


def test_a_librarys_own_library_json_is_reported_with_its_files(library, project, nobody, no_network, capsys):
    root = project()
    _install(library(extra={"extras": ["library.json"]}, files={"library.json": '{"name": "demo"}\n'}),
             "--project", root)
    capsys.readouterr()

    assert _uninstall("demo", "--project", root) == 0

    assert "removed lib/demo/library.json" in capsys.readouterr().out
