"""
library.json: how a library in the project's lib folder introduces itself to PlatformIO.

PlatformIO's Library Dependency Finder reads it for which files to build, the
folder a project includes from, the frameworks and platforms the library builds
with, and the libraries of the PlatformIO Registry it needs, which PlatformIO
then installs itself. A library written for any project has none, so it is
written here, from installer.yml, and written again on every install.

It names the library's files one by one, from installer.yml, so PlatformIO
builds those and nothing else: a test or an example in the library's folder is
left alone, and a source file a new version adds is built with no one editing
anything.

A library made for PlatformIO ships its own, which knows the library better
than this does, and is left alone. JSON has no comments to mark this one with,
so the two are told apart by whether installer.yml lists a library.json among
the library's own files.
"""

import json
import re
from pathlib import Path

from .core.target import ALREADY, CHANGED, MANUAL, Outcome

NAME = "library.json"

_OWNER = re.compile(r"github\.com[/:]([^/\s]+)/", re.IGNORECASE)


def ships_its_own(library):
    """Whether installer.yml lists a library.json among the library's files."""
    entries = list(library.headers) + list(library.sources) + list(library.extras) + list(library.once)

    return any(Path(getattr(entry, "destination", "")).as_posix() == NAME for entry in entries)


def _author(library):
    found = _OWNER.search(library.repository or "")

    return found.group(1) if found else None


def manifest(library):
    """library.json for this library, as a dict in the order it is written."""
    data = {"name": library.name}

    if library.version:
        data["version"] = library.version

    if library.description:
        data["description"] = library.description

    keywords = [word for word in (library.kind, library.category) if word]

    if keywords:
        data["keywords"] = keywords

    if library.repository:
        data["repository"] = {"type": "git", "url": library.repository}

    author = _author(library)

    if author:
        data["authors"] = [{"name": author}]

    if library.license:
        data["license"] = library.license

    data["frameworks"] = library.pio.frameworks or "*"
    data["platforms"] = library.pio.platforms or "*"

    if library.pio.dependencies:
        data["dependencies"] = dict(library.pio.dependencies)

    # Built from the top of its folder, with every file but its own sources
    # filtered out. Its include folder is the one a project includes it from.
    build = {
        "srcDir": ".",
        "srcFilter": ["-<*>"] + [f"+<{name}>" for name in library.build_sources],
    }
    main, others = _include_folders(library)

    if main:
        build["includeDir"] = main

    if others:
        build["flags"] = [f"-I {folder}" for folder in others]

    data["build"] = build

    return data


def _include_folders(library):
    """
    The include folder, and any other folder the headers are in.

    The include folder is the first one install.include_dirs names, or else the
    folder of the first header, the one a project includes. library.json has
    room for one, so the others go in as -I flags, which PlatformIO gives the
    library and every file that uses it alike (measured). The top of the
    library is on the include path already, as its srcDir.
    """
    if library.declared_include_dirs:
        first = library.declared_include_dirs[0]
    elif library.headers:
        first = library.headers[0].folder
    else:
        first = None

    main = first if first not in (None, ".", "") else None
    others = [folder for folder in library.include_dirs if folder not in (".", "", main)]

    return main, others


def text(library):
    """The file's text: JSON, two space indents, a line ending at the end."""
    return json.dumps(manifest(library), indent=2) + "\n"


def write(library, destination):
    """Write library.json, only when it changed. Returns an Outcome."""
    path = Path(destination) / NAME

    if ships_its_own(library):
        return Outcome(NAME, ALREADY, f"{library.name} has its own library.json, used as it is.")

    data = text(library).encode("utf-8")

    try:
        if path.is_file() and path.read_bytes() == data:
            return Outcome(NAME, ALREADY, f"{library.name}'s library.json is up to date.")

        path.write_bytes(data)
    except OSError as error:
        return Outcome(NAME, MANUAL, f"Could not write {path}: {error}")

    return Outcome(NAME, CHANGED, f"Wrote {library.name}'s library.json, which PlatformIO builds it by.")


def remove(installed):
    """
    Delete the library.json write() made, before the library's files go. One
    the record lists as the library's own is left to go with them.
    """
    if installed.destination is None:
        return

    path = Path(installed.destination) / NAME

    if path in installed.files or path in installed.once:
        return

    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass
