"""The whole command, from the command line to the files it leaves, and what it checks first."""

import json

import pytest
from conftest import read

from pio_installer import __version__
from pio_installer.core import cli, manifest, target
from pio_installer.core.target import INFO, MANUAL, WARN


def _install(*args):
    return cli.main([str(arg) for arg in args])


def test_the_version_is_the_packages(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--version"])

    assert capsys.readouterr().out.strip() == f"pio-installer {__version__}"


def test_the_help_names_a_platformio_project(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])

    out = capsys.readouterr().out
    assert "PlatformIO project" in out
    assert "--ide" not in out


def test_a_library_goes_into_lib_with_its_library_json(library, project, nobody, no_network, capsys):
    root = project()

    assert _install(library(defines=["DEMO_FAST"]), "--project", root) == 0

    folder = root / "lib" / "demo"
    assert (folder / "src" / "demo.h").is_file()
    assert json.loads(read(folder / "library.json"))["build"]["srcFilter"] == ["-<*>", "+<src/demo.c>"]
    assert "    -DDEMO_FAST\n" in read(root / "platformio.ini")
    assert json.loads(read(root / ".pio-installer.json"))["libraries"]["demo"]["folder"] == "lib/demo"
    assert 'Done. #include "demo.h" and you are away.' in capsys.readouterr().out


def test_a_library_with_no_defines_leaves_platformio_ini_alone(library, project, nobody, no_network):
    root = project()

    assert _install(library(), "--project", root) == 0

    assert read(root / "platformio.ini") == "[env:native]\nplatform = native\n"
    assert not list(root.glob("platformio.ini.*.bak"))


def test_what_a_library_needs_goes_into_lib_too(library, project, nobody, no_network, tmp_path):
    root = project()
    helper = library(name="helper", root=tmp_path / "repos" / "helper")
    demo = library(requires={"libraries": ["helper"]})

    assert _install(demo, helper, "--project", root) == 0

    assert (root / "lib" / "helper" / "library.json").is_file()
    assert (root / "lib" / "demo" / "library.json").is_file()


def test_the_folder_offered_is_in_lib(library, project, answers, no_network):
    asked = answers("")

    assert _install(library(), "--project", project()) == 0

    assert "[lib/demo]" in asked[0]


def test_a_folder_outside_lib_is_named_for_the_user(library, project, nobody, no_network, capsys):
    root = project()

    assert _install(library(), "--project", root, "--dir", "vendor/demo") == 0

    out = capsys.readouterr().out
    assert "PlatformIO looks for libraries in lib/, and demo is not in it." in out
    assert "lib_extra_dirs" in out


# ----------------------------------------------------------------------------
# What is checked before the library goes in
# ----------------------------------------------------------------------------


def _check(library, root, **kwargs):
    return target.current.check(manifest.load(library(**kwargs)), root)


def test_no_platformio_ini_is_one_warning(library, tmp_path):
    found = _check(library, tmp_path)

    assert [(f.level, f.message) for f in found] == [(WARN, "No platformio.ini here")]


def test_an_environment_the_library_does_not_build_with_is_named(library, project):
    ini = ("[env]\nframework = arduino\n\n[env:uno]\nplatform = atmelavr\n\n"
           "[env:esp]\nplatform = platformio/espressif32@^6.5\nframework = espidf\n\n"
           "[env:pc]\nplatform = native\nframework =\n")

    found = _check(library, project(ini=ini), pio={"frameworks": ["arduino"], "platforms": ["atmelavr", "native"]})

    assert [(f.level, f.message) for f in found] == [
        (WARN, "[env:esp] builds with espidf, which demo does not list, so PlatformIO leaves it out of that build"),
    ]


def test_a_platform_the_library_does_not_list_is_named(library, project):
    found = _check(library, project(ini="[env:esp]\nplatform = espressif32\n"), pio={"platforms": ["native"]})

    assert found[0].level == WARN
    assert "[env:esp] builds for espressif32" in found[0].message


def test_a_platform_from_a_url_is_not_judged(library, project):
    ini = "[env:x]\nplatform = https://github.com/someone/platform-x.git\n"

    assert _check(library, project(ini=ini), pio={"platforms": ["native"]}) == []


def test_defines_dependencies_and_hardware_are_said(library, project):
    found = _check(library, project(), defines=["DEMO_FAST"],
                   pio={"dependencies": ["bblanchon/ArduinoJson@^7.0.0", "Wire"]},
                   requires={"peripherals": [{"type": "i2c", "note": "400 kHz"}, "spi"]})

    assert [(f.level, f.message) for f in found] == [
        (INFO, "DEMO_FAST goes into build_flags in platformio.ini"),
        (INFO, "Needs bblanchon/ArduinoJson ^7.0.0, from the PlatformIO Registry"),
        (INFO, "Needs Wire, from the PlatformIO Registry"),
        (INFO, "Needs I2C, 400 kHz"),
        (INFO, "Needs SPI"),
    ]


def test_an_unreadable_platformio_ini_gives_the_flags_by_hand(library, tmp_path):
    from pio_installer import ini

    loaded = manifest.load(library(defines=["DEMO_FAST"]))
    outcome = ini.integrate(tmp_path, loaded)

    assert outcome.status == MANUAL
    assert outcome.steps[-1] == "-DDEMO_FAST"


def test_a_platform_with_its_owner_and_version_is_the_platform(library, project):
    ini = "[env:esp]\nplatform = platformio/espressif32@^6.5\n"

    assert _check(library, project(ini=ini), pio={"platforms": ["espressif32"]}) == []
