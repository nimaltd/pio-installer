"""
platformio.ini: the defines a library gives the whole project.

A define in a library's library.json reaches only the library's own files, as
measured: the project's own code, which includes the library's header, never
sees it. A define can change what that header declares, and every file that
includes it has to agree, so a library's install.defines go into platformio.ini
instead, where PlatformIO hands build_flags to every file of the build.

Each library's defines are a marked block inside build_flags:

    build_flags =
        -DFROM_YOU=1
        ; >>> pio-installer: example >>>
        -DEXAMPLE_FAST
        ; <<< pio-installer: example <<<

A block goes wherever build_flags reaches an environment: into [env], which
every [env:name] without build_flags of its own takes, and into each
[env:name] that has its own, since it takes nothing from [env]. A project with
no [env] section and an environment without build_flags gets an [env] section
for them. An uninstall takes out the blocks, and what was added to hold them,
so the file is back as it was.

The file is the user's, so it is edited as text, never through a parser that
would drop its comments: a copy is taken before it changes, its line endings
are kept, and a second install adds nothing twice.
"""

import re
from pathlib import Path

from .core.files import backup
from .core.target import ALREADY, CHANGED, MANUAL, Outcome

NAME = "platformio.ini"

MARK_OPEN = "; >>> pio-installer: {name} >>>"
MARK_CLOSE = "; <<< pio-installer: {name} <<<"

_SECTION = re.compile(r"^\[([^\]]+)\][ \t]*$")
_FLAGS = re.compile(r"^build_flags[ \t]*=(.*)$")
_FRAMEWORK = re.compile(r"^framework[ \t]*=[ \t]*(.*?)[ \t]*$")
_PLATFORM = re.compile(r"^platform[ \t]*=[ \t]*(.*?)[ \t]*$")

INDENT = "    "


def read(path):
    """The file's text, with its line endings exactly as they are on disk."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return handle.read()


def write(path, text):
    """Write the text back with its line endings untouched."""
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def line_ending(text):
    """The line ending the file already uses, line feed for a new one."""
    return "\r\n" if "\r\n" in text else "\n"


def sections(lines):
    """Every section: (name, the line of its header, the line after its last)."""
    found = [(match.group(1).strip(), index) for index, line in enumerate(lines)
             for match in [_SECTION.match(line)] if match]

    return [(name, start, found[k + 1][1] if k + 1 < len(found) else len(lines))
            for k, (name, start) in enumerate(found)]


def flags(lines, start, end):
    """build_flags in a section: (its line, its last value line), or None."""
    for index in range(start + 1, end):
        if _FLAGS.match(lines[index]):
            last = index

            while last + 1 < end and lines[last + 1][:1] in (" ", "\t") and lines[last + 1].strip():
                last += 1

            return index, last

    return None


def environments(text):
    """
    Each [env:name], with the framework and the platform it builds with:
    {name: (frameworks, platform)}. One it does not set itself comes from [env].
    """
    lines = text.splitlines()
    common = {"framework": "", "platform": ""}
    found = {}

    for name, start, end in sections(lines):
        values = {}

        for line in lines[start + 1:end]:
            for key, pattern in (("framework", _FRAMEWORK), ("platform", _PLATFORM)):
                match = pattern.match(line)

                if match:
                    values[key] = match.group(1)

        if name == "env":
            common.update(values)
        elif name.startswith("env:"):
            found[name[len("env:"):]] = (values.get("framework", common["framework"]),
                                         values.get("platform", common["platform"]))

    return {env: ([f.strip() for f in framework.split(",") if f.strip()], platform)
            for env, (framework, platform) in found.items()}


def _block(name, defines, indent):
    lines = [indent + MARK_OPEN.format(name=name)]
    lines += [f"{indent}-D{define}" for define in defines]
    lines.append(indent + MARK_CLOSE.format(name=name))

    return lines


def _indent(lines, key, last):
    """The indent of the value lines already there, or the usual four spaces."""
    for line in lines[key + 1:last + 1]:
        return line[:len(line) - len(line.lstrip(" \t"))] or INDENT

    return INDENT


def without(lines, name):
    """
    The lines with this library's blocks taken out, and what was there only to
    hold them: a build_flags left with no value, and an [env] left empty.
    """
    open_mark = MARK_OPEN.format(name=name)
    close_mark = MARK_CLOSE.format(name=name)
    kept = []
    inside = False
    held = set()

    for line in lines:
        if line.strip() == open_mark:
            inside = True

            # The build_flags this block was in, which may now hold nothing.
            for back in range(len(kept) - 1, -1, -1):
                if _FLAGS.match(kept[back]):
                    held.add(back)
                    break

                if not kept[back][:1] in (" ", "\t"):
                    break

            continue

        if inside:
            inside = line.strip() != close_mark
            continue

        kept.append(line)

    # A build_flags with nothing on its line and nothing after it any more.
    emptied = {index for index in held
               if not _FLAGS.match(kept[index]).group(1).strip()
               and not (index + 1 < len(kept) and kept[index + 1][:1] in (" ", "\t") and kept[index + 1].strip())}
    kept = [line for index, line in enumerate(kept) if index not in emptied]

    # An [env] that held nothing but the emptied build_flags, with the blank
    # line it brought. A comment of the user's in it keeps it.
    if emptied:
        for section, start, end in reversed(sections(kept)):
            if section == "env" and not any(line.strip() for line in kept[start + 1:end]):
                del kept[start:end]

    return kept


def with_block(lines, name, defines):
    """The lines with this library's defines added wherever build_flags reaches an environment."""
    found = sections(lines)
    common = next((s for s in found if s[0] == "env"), None)
    envs = [s for s in found if s[0].startswith("env:")]
    inserts = []

    for _section, start, end in envs:
        span = flags(lines, start, end)

        if span:
            inserts.append((span[1] + 1, _block(name, defines, _indent(lines, *span))))

    if common is not None:
        _section, start, end = common
        span = flags(lines, start, end)

        if span:
            inserts.append((span[1] + 1, _block(name, defines, _indent(lines, *span))))
        else:
            last = max([start] + [i for i in range(start + 1, end) if lines[i].strip()])
            inserts.append((last + 1, ["build_flags ="] + _block(name, defines, INDENT)))
    elif any(flags(lines, start, end) is None for _section, start, end in envs):
        first = envs[0][1]
        inserts.append((first, ["[env]", "build_flags ="] + _block(name, defines, INDENT) + [""]))

    for index, added in sorted(inserts, key=lambda item: item[0], reverse=True):
        lines[index:index] = added

    return lines


def _split(text):
    newline = line_ending(text)
    lines = text.split(newline)

    return newline, lines


def updated(text, name, defines):
    """The file's text with this library's defines, or none of them when it has none."""
    newline, lines = _split(text)
    lines = without(lines, name)

    if defines:
        lines = with_block(lines, name, defines)

    return newline.join(lines)


def integrate(project_root, library):
    """Give the project the library's defines. Returns an Outcome, or None when there is nothing to do."""
    path = Path(project_root) / NAME

    try:
        text = read(path)
    except (OSError, UnicodeDecodeError) as error:
        if not library.defines:
            return None

        return Outcome(NAME, MANUAL, f"Could not read {NAME}: {error}",
                       ["Add these to build_flags of every environment:"]
                       + [f"-D{define}" for define in library.defines])

    new = updated(text, library.name, library.defines)

    if new == text:
        return Outcome(NAME, ALREADY, f"{NAME} already has {library.name}'s defines.") if library.defines else None

    saved = backup(path)
    write(path, new)
    what = f"Added {library.name}'s defines to" if library.defines else f"Took {library.name}'s old defines out of"

    return Outcome(NAME, CHANGED, f"{what} {NAME}, for every environment.", backup=saved)


def uninstall(project_root, name):
    """Take this library's defines out of platformio.ini. An Outcome, or None."""
    path = Path(project_root) / NAME

    try:
        text = read(path)
    except (OSError, UnicodeDecodeError):
        return None

    new = updated(text, name, [])

    if new == text:
        return None

    saved = backup(path)
    write(path, new)

    return Outcome(NAME, CHANGED, f"Removed {name}'s defines from {NAME}.", backup=saved)
