"""The pio section of installer.yml, and the library.json written from it."""

import json

import pytest
from conftest import read

from pio_installer import library_json
from pio_installer.core import manifest
from pio_installer.core.manifest import ManifestError
from pio_installer.core.target import ALREADY, CHANGED


def _loaded(library, **kwargs):
    return manifest.load(library(**kwargs))


def test_with_no_pio_part_it_builds_anywhere(library):
    data = library_json.manifest(_loaded(library))

    assert data == {
        "name": "demo",
        "version": "1.2.0",
        "description": "A library for the tests",
        "keywords": ["utility", "timing"],
        "repository": {"type": "git", "url": "https://github.com/someone/demo"},
        "authors": [{"name": "someone"}],
        "license": "Apache-2.0",
        "frameworks": "*",
        "platforms": "*",
        "build": {"srcDir": ".", "srcFilter": ["-<*>", "+<src/demo.c>"], "includeDir": "src"},
    }


def test_the_pio_part_is_written_as_given(library):
    data = library_json.manifest(_loaded(library, pio={
        "frameworks": ["arduino", "espidf"], "platforms": "espressif32",
        "dependencies": ["bblanchon/ArduinoJson@^7.0.0", "Wire"],
    }))

    assert data["frameworks"] == ["arduino", "espidf"]
    assert data["platforms"] == ["espressif32"]
    assert data["dependencies"] == {"bblanchon/ArduinoJson": "^7.0.0", "Wire": "*"}


def test_only_its_own_sources_are_built(library):
    loaded = _loaded(library, sources=("src/demo.c", "src/port/spi.c"), files={"test/test_demo.c": "x\n"})

    assert library_json.manifest(loaded)["build"]["srcFilter"] == ["-<*>", "+<src/demo.c>", "+<src/port/spi.c>"]


def test_a_library_at_the_top_has_no_include_folder(library):
    data = library_json.manifest(_loaded(library, headers=("demo.h",), sources=("demo.c",), layout="flat"))

    assert "includeDir" not in data["build"]
    assert "flags" not in data["build"]


def test_the_first_headers_folder_is_the_include_folder_and_the_others_are_flags(library):
    loaded = _loaded(library, headers=("inc/demo.h", "api/demo_api.h", "inc/port/demo_port.h", "top.h"))

    build = library_json.manifest(loaded)["build"]

    assert build["includeDir"] == "inc"
    assert build["flags"] == ["-I api", "-I inc/port"]


def test_include_dirs_named_in_installer_yml_come_first(library):
    loaded = _loaded(library, headers=("src/demo.h", "include/demo_port.h"),
                     extra={"install": {"layout": "mirror", "include_dirs": ["include", "src"]}})

    build = library_json.manifest(loaded)["build"]

    assert build["includeDir"] == "include"
    assert build["flags"] == ["-I src"]


@pytest.mark.parametrize("pio, message", [
    ({"frameworks": ["Arduino IDE"]}, "pio.frameworks"),
    ({"platforms": [1.5]}, "pio.platforms"),
    ({"dependencies": "ArduinoJson"}, "pio.dependencies"),
    ({"dependencies": ["bad;name"]}, "pio.dependencies"),
    ("everything", "pio should hold"),
])
def test_what_cannot_be_written_is_refused(library, pio, message):
    with pytest.raises(ManifestError, match=message):
        _loaded(library, pio=pio)


@pytest.mark.parametrize("value", ["*", ["*"], None])
def test_any_is_written_as_a_star(library, value):
    loaded = _loaded(library, pio={"frameworks": value})

    assert library_json.manifest(loaded)["frameworks"] == "*"


def test_it_is_written_as_json_then_left_alone(library, tmp_path):
    loaded = _loaded(library)
    folder = tmp_path / "demo"
    folder.mkdir()

    assert library_json.write(loaded, folder).status == CHANGED
    assert json.loads(read(folder / "library.json"))["name"] == "demo"
    assert read(folder / "library.json").endswith("}\n")
    assert library_json.write(loaded, folder).status == ALREADY


def test_a_librarys_own_is_used_as_it_is(library, tmp_path):
    loaded = _loaded(library, extra={"extras": ["library.json"]}, files={"library.json": '{"name": "mine"}\n'})
    folder = tmp_path / "demo"
    folder.mkdir()
    (folder / "library.json").write_bytes(b'{"name": "mine"}\n')

    assert library_json.ships_its_own(loaded)
    assert library_json.write(loaded, folder).status == ALREADY
    assert read(folder / "library.json") == '{"name": "mine"}\n'


def test_frameworks_may_be_one_line_with_commas(library):
    loaded = _loaded(library, pio={"frameworks": "arduino, espidf"})

    assert library_json.manifest(loaded)["frameworks"] == ["arduino", "espidf"]
