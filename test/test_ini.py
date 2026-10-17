"""platformio.ini: where a library's defines go, and that taking them out gives the file back."""

import pytest

from pio_installer import ini


def _add(text, name="demo", defines=("DEMO_FAST",)):
    return ini.updated(text, name, list(defines))


def _round(text, name="demo", defines=("DEMO_FAST",)):
    """Added, then taken out: the text it comes back as."""
    return ini.updated(_add(text, name, defines), name, [])


def test_an_env_with_no_build_flags_gets_an_env_section_above_it():
    text = "[platformio]\ndefault_envs = native\n\n[env:native]\nplatform = native\n"

    assert _add(text) == (
        "[platformio]\ndefault_envs = native\n\n"
        "[env]\nbuild_flags =\n    ; >>> pio-installer: demo >>>\n    -DDEMO_FAST\n    ; <<< pio-installer: demo <<<\n\n"
        "[env:native]\nplatform = native\n"
    )


def test_an_env_with_its_own_build_flags_gets_the_block_in_them():
    text = "[env:native]\nplatform = native\nbuild_flags =\n\t-DYOURS=1\nlib_deps = x\n"

    assert _add(text) == (
        "[env:native]\nplatform = native\nbuild_flags =\n\t-DYOURS=1\n"
        "\t; >>> pio-installer: demo >>>\n\t-DDEMO_FAST\n\t; <<< pio-installer: demo <<<\nlib_deps = x\n"
    )


def test_a_build_flags_on_one_line_takes_the_block_under_it():
    text = "[env:native]\nbuild_flags = -DYOURS=1\n"

    assert _add(text) == ("[env:native]\nbuild_flags = -DYOURS=1\n"
                          "    ; >>> pio-installer: demo >>>\n    -DDEMO_FAST\n    ; <<< pio-installer: demo <<<\n")


def test_an_env_section_without_build_flags_gets_them_and_no_second_env():
    text = "[env]\nframework = arduino\n\n[env:uno]\nplatform = atmelavr\n"

    assert _add(text) == (
        "[env]\nframework = arduino\nbuild_flags =\n    ; >>> pio-installer: demo >>>\n    -DDEMO_FAST\n"
        "    ; <<< pio-installer: demo <<<\n\n[env:uno]\nplatform = atmelavr\n"
    )


def test_both_env_and_an_env_with_its_own_get_a_block():
    text = "[env]\nbuild_flags = -DCOMMON\n\n[env:a]\nplatform = native\n\n[env:b]\nbuild_flags = -DB\n"

    added = _add(text)

    assert added.count(">>> pio-installer: demo >>>") == 2
    assert added.startswith("[env]\nbuild_flags = -DCOMMON\n    ; >>> pio-installer: demo >>>")
    assert "[env:a]\nplatform = native\n\n" in added


def test_installing_twice_writes_one_block():
    text = "[env:native]\nplatform = native\n"

    assert _add(_add(text)) == _add(text)


def test_new_defines_replace_the_old():
    text = _add("[env:native]\nplatform = native\n", defines=["OLD=1", "GONE"])

    assert _add(text, defines=["NEW=2"]) == _add("[env:native]\nplatform = native\n", defines=["NEW=2"])


def test_no_defines_now_takes_the_block_out():
    text = "[env:native]\nplatform = native\n"

    assert ini.updated(_add(text), "demo", []) == text


def test_two_libraries_keep_a_block_each():
    text = _add(_add("[env:native]\nplatform = native\n", "one", ["ONE"]), "two", ["TWO"])

    assert text.count(">>> pio-installer: one >>>") == 1
    assert text.count(">>> pio-installer: two >>>") == 1
    assert ini.updated(ini.updated(text, "two", []), "one", []) == "[env:native]\nplatform = native\n"


@pytest.mark.parametrize("text", [
    "[env:native]\nplatform = native\n",
    "[env:native]\nplatform = native\nbuild_flags =\n    -DYOURS\n",
    "[env:native]\nbuild_flags = -DYOURS\n",
    "[env]\nframework = arduino\n\n[env:uno]\nplatform = atmelavr\n",
    "[env]\nbuild_flags = -DC\n\n[env:a]\nplatform = native\n\n[env:b]\nbuild_flags = -DB\n",
    "; mine\n[platformio]\ndefault_envs = a\n\n[env:a]\nplatform = native\n\n[env:b]\nplatform = native\n",
    "[env:native]\nplatform = native",
])
def test_taken_out_again_the_file_is_back_to_the_byte(text):
    assert _round(text) == text
    assert _round(text.replace("\n", "\r\n")) == text.replace("\n", "\r\n")


def test_crlf_is_kept_in_what_is_added():
    added = _add("[env:native]\r\nplatform = native\r\n")

    assert "\n" not in added.replace("\r\n", "")


def test_a_block_of_another_library_is_left_alone():
    text = _add("[env:native]\nplatform = native\n", "other", ["OTHER"])

    assert ini.updated(text, "demo", []) == text


def test_the_environments_and_what_they_build_with():
    text = ("[env]\nframework = arduino\nplatform = atmelavr\n\n[env:uno]\nboard = uno\n\n"
            "[env:esp]\nplatform = platformio/espressif32@^6.5\nframework = arduino, espidf\n")

    assert ini.environments(text) == {
        "uno": (["arduino"], "atmelavr"),
        "esp": (["arduino", "espidf"], "platformio/espressif32@^6.5"),
    }


def test_a_line_of_spaces_ends_the_value():
    text = "[env:native]\nbuild_flags = -DA\n   \nlib_deps = x\n"

    assert _add(text) == ("[env:native]\nbuild_flags = -DA\n"
                          "    ; >>> pio-installer: demo >>>\n    -DDEMO_FAST\n    ; <<< pio-installer: demo <<<\n"
                          "   \nlib_deps = x\n")


def test_an_env_of_only_the_users_comments_stays(text="[env]\n; my notes\n\n[env:a]\nplatform = native\n"):
    assert _round(text) == text
