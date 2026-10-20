"""
What pio-installer adds to the shared core: what a PlatformIO project is.

A library goes into the project's lib folder, which PlatformIO's Library
Dependency Finder searches for every framework it builds with, and where one
library finds another: measured, a library in lib/ including the header of
another in lib/ builds, so what a library needs goes there too. Each gets a
library.json (library_json.py), and the defines it needs go into
platformio.ini (ini.py), since a define in library.json reaches the library's
own files and nothing else.
"""

import re
from pathlib import Path

from . import ini, library_json
from .core.manifest import ManifestError
from .core.target import INFO, MANUAL, WARN, Finding, Outcome, Target

LIB = "lib"

# A framework or a platform as platformio.ini names it: arduino, espidf,
# stm32cube, espressif32, ststm32, native.
_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# A library of the PlatformIO Registry: owner/name, with @version when one is needed.
_REGISTRY = re.compile(r"^(?:[A-Za-z0-9_.-]+/)?[A-Za-z0-9 _.+-]+(?:@\S+)?$")


def _names(data, key):
    """frameworks or platforms: a list of names, or [] for any."""
    value = data.get(key)

    if value is None or value == "*" or value == ["*"]:
        return []

    if isinstance(value, str):
        value = [part.strip() for part in value.split(",")]

    if not isinstance(value, list) or not all(_NAME.match(str(name)) for name in value):
        raise ManifestError(
            f"pio.{key} is a list of names as platformio.ini writes them, such as "
            f"{'[arduino, espidf]' if key == 'frameworks' else '[espressif32, ststm32]'}, or \"*\" for any."
        )

    return [str(name) for name in value]


class PioPart:
    """The pio section of installer.yml, with what it leaves out filled in."""

    def __init__(self, data):
        if data is None:
            data = {}

        if not isinstance(data, dict):
            raise ManifestError("pio should hold frameworks, platforms and dependencies.")

        self.frameworks = _names(data, "frameworks")
        self.platforms = _names(data, "platforms")

        dependencies = data.get("dependencies") or []

        if not isinstance(dependencies, list) or not all(_REGISTRY.match(str(d).strip()) for d in dependencies):
            raise ManifestError(
                "pio.dependencies is a list of PlatformIO Registry libraries, such as "
                "[bblanchon/ArduinoJson@^7.0.0]: owner/name, and @version when one is needed."
            )

        # As library.json writes them: {"owner/name": "version"}, * for any.
        self.dependencies = {}

        for entry in dependencies:
            name, _, version = str(entry).strip().partition("@")
            self.dependencies[name] = version or "*"


def _platform(text):
    """A platform from platformio.ini as a plain name: espressif32 from platformio/espressif32@^6.5."""
    name = text.split("@")[0].strip()

    return None if "://" in name or name.endswith(".git") else name.split("/")[-1]


class PlatformIO(Target):
    """A PlatformIO project: platformio.ini, src/, and lib/ for its libraries."""

    name = "pio-installer"
    record_name = ".pio-installer.json"
    project = "PlatformIO project"
    requires_key = "pio_installer"
    no_project = "No platformio.ini here, so nothing was registered."
    no_project_hint = "Run this from your project's folder, the one holding platformio.ini."

    def __init__(self, version):
        self.version = version

    def managed_files(self, project_root, library):
        """platformio.ini, which this edits, and which a once file must never be."""
        return [self.record_name, ini.NAME]

    def default_folder(self, library):
        """Libraries go into lib/, which PlatformIO searches for every framework."""
        return f"{LIB}/{library.name}"

    def read_manifest(self, manifest, data):
        manifest.pio = PioPart(data.get("pio"))

    def read_requirements(self, requirements, data):
        """Hardware the library uses, named to the user: I2C, or I2C, 400 kHz."""
        found = []

        for entry in data.get("peripherals") or []:
            if isinstance(entry, dict):
                note = entry.get("note")
                found.append(str(entry.get("type", "")).upper() + (f", {note}" if note else ""))
            else:
                found.append(str(entry).upper())

        requirements.peripherals = found

    def requirements_empty(self, requirements):
        return not requirements.peripherals

    def check(self, library, project_root):
        """What the project is missing for this library. Never stops an install."""
        path = Path(project_root) / ini.NAME

        try:
            text = ini.read(path)
        except (OSError, UnicodeDecodeError):
            return [Finding(WARN, "No platformio.ini here",
                            "Run this from your PlatformIO project's folder, or give it with --project.")]

        findings = []
        wanted = library.pio

        # PlatformIO leaves a library a build cannot use out of that build
        # without a word, and its header is then simply not found.
        for env, (frameworks, platform) in ini.environments(text).items():
            missing = [f for f in frameworks if wanted.frameworks and f not in wanted.frameworks]
            plain = _platform(platform) if platform else None

            if missing:
                findings.append(Finding(
                    WARN, f"[env:{env}] builds with {', '.join(missing)}, which {library.name} does not list, "
                    "so PlatformIO leaves it out of that build",
                    f"{library.name} lists: {', '.join(wanted.frameworks)}.",
                ))
            elif wanted.platforms and plain and plain not in wanted.platforms:
                findings.append(Finding(
                    WARN, f"[env:{env}] builds for {plain}, which {library.name} does not list, "
                    "so PlatformIO leaves it out of that build",
                    f"{library.name} lists: {', '.join(wanted.platforms)}.",
                ))

        if library.defines:
            findings.append(Finding(INFO, f"{', '.join(library.defines)} goes into build_flags in platformio.ini"))

        for name, version in wanted.dependencies.items():
            findings.append(Finding(INFO, f"Needs {name}{'' if version == '*' else ' ' + version}, from the "
                                    "PlatformIO Registry", "PlatformIO installs it by itself at the next build."))

        for peripheral in library.requires.peripherals:
            findings.append(Finding(INFO, f"Needs {peripheral}", "Set it up in your code."))

        return findings

    def integrate(self, project_root, library, destination, only=None, dropped=(), dropped_defines=()):
        """
        Write the library's library.json, and its defines into platformio.ini.

        dropped needs nothing here: library.json names the files of the new
        version only. dropped_defines needs nothing either: the block of
        defines is written again from the new manifest, so one that has gone is
        no longer in it.
        """
        outcomes = [library_json.write(library, destination)]
        outcome = ini.integrate(project_root, library)

        if outcome is not None:
            outcomes.append(outcome)

        try:
            in_lib = Path(destination).resolve().parent == (Path(project_root) / LIB).resolve()
        except OSError:
            in_lib = True

        if not in_lib:
            outcomes.append(Outcome(
                "lib_extra_dirs", MANUAL,
                f"PlatformIO looks for libraries in {LIB}/, and {library.name} is not in it.",
                [f"Add its folder's parent to lib_extra_dirs in the [env] section of {ini.NAME}, "
                 f"or install it into {LIB}/ with --dir {LIB}/{library.name}."],
            ))

        return outcomes

    def uninstall(self, project_root, library):
        """Its library.json and its defines go, before its files do."""
        library_json.remove(library)
        outcome = ini.uninstall(project_root, library.name)

        return [outcome] if outcome is not None else []
