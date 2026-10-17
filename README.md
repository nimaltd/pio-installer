# pio-installer

Installs embedded C and C++ libraries into a PlatformIO project, from GitHub, from a zip, or from a folder, for any framework.

It puts a library into your project's `lib` folder, which PlatformIO builds from for every framework: Arduino, ESP-IDF, STM32Cube, or none at all on the native platform. A library written for any project gets the `library.json` PlatformIO builds it by, the defines it needs go into `platformio.ini`, the libraries it needs go in first, and its settings are kept through every update.

It works with any library that has an `installer.yml` at the root of its repository. I wrote it for my own [NimaLTD](https://github.com/nimaltd) libraries, and they all have one, but nothing in it is tied to them: add an `installer.yml` to yours, as shown [below](#for-someone-writing-a-library), and it installs the same way. The same file serves [stm32-installer](https://github.com/nimaltd/stm32-installer), [zephyr-installer](https://github.com/nimaltd/zephyr-installer), [esp32-installer](https://github.com/nimaltd/esp32-installer) and [arduino-installer](https://github.com/nimaltd/arduino-installer).

PlatformIO from the command line and the PlatformIO IDE in VS Code both build what it installs, since `lib` is where PlatformIO itself looks.

Every command below uses `owner/example`, the library's GitHub owner and name, such as `nimaltd/ee24`. Put the real ones in its place.

---

## Installing a library

Install the installer once. This needs internet:

```bash
pip install pio-installer
```

Then, from your project's folder, the one holding `platformio.ini`, install a library by its GitHub owner and name. To see it work first, take [pio-installer-example](https://github.com/nimaltd/pio-installer-example), a library made for trying the installer on:

```bash
pio-installer nimaltd/pio-installer-example
```

It builds with every framework, and on the native platform too, so you can run it on your computer with no board at all. Its README walks through a setting kept through an update, an option, and an uninstall. Any other library goes in the same way, as `pio-installer owner/example`.

To update it later, `pip install --upgrade pio-installer`. To remove it, `pip uninstall pio-installer`.

On Windows, if `pio-installer` is not found after installing, pip put it in a folder that is not on your PATH. `python -m pio_installer owner/example` runs the same thing.

### Where a library goes

Into `lib`, in a folder of its own:

```
my-project/
  platformio.ini            the defines of a library that has some, in build_flags
  .pio-installer.json       what is installed here, and where
  src/
    main.c
  lib/
    example/
      library.json          written by the installer: how PlatformIO builds the library
      src/
        example.h           the library's files, as its installer.yml lists them
        example_config.h    its settings, between USER CODE lines
        example.c
```

PlatformIO builds a library of `lib` once your code includes one of its headers, for every environment in `platformio.ini`, so the library is your project's own, with your project's settings. You include it by its name:

```c
#include "example.h"
```

The installer asks for the folder, with `lib/example` as the answer when you just press Enter. A folder outside `lib` works too, given with `--dir`, but PlatformIO does not look there, so the installer says what to add to `platformio.ini`:

```
Project
  manual  lib_extra_dirs  PlatformIO looks for libraries in lib/, and example is not in it.
          Add its folder's parent to lib_extra_dirs in the [env] section of platformio.ini, or install it into lib/ with --dir lib/example.
```

### library.json

PlatformIO builds a library by its `library.json`. A library written for any project has none, so the installer writes one from the library's `installer.yml`, and writes it again on every install:

```json
{
  "name": "example",
  "version": "1.0.0",
  "frameworks": "*",
  "platforms": "*",
  "build": {
    "srcDir": ".",
    "srcFilter": ["-<*>", "+<src/example.c>"],
    "includeDir": "src"
  }
}
```

It names the library's source files one by one, so PlatformIO builds those and nothing else: a test or an example in the library's folder is left alone. Its description, licence, repository and author go in too, and the frameworks, platforms and PlatformIO Registry libraries the library lists, as [below](#for-someone-writing-a-library).

A library made for PlatformIO that ships its own `library.json`, listed in its `installer.yml` so it is installed, keeps it: the installer writes one only for a library that has none.

### Defines

A library that needs a define for the whole build, such as littlefs's `LFS_DEFINES`, lists it in its `installer.yml`, and the installer puts it into `build_flags` in `platformio.ini`, between two lines that say whose it is:

```ini
[env]
build_flags =
    ; >>> pio-installer: example >>>
    -DEXAMPLE_FAST
    ; <<< pio-installer: example <<<

[env:uno]
platform = atmelavr
board = uno
framework = arduino
```

`[env]` is shared by every environment, so that is where it goes, and the installer adds the section when an environment needs it and the file has none. An environment with `build_flags` of its own does not take them from `[env]`, so it gets the same lines in its own. Everything else in the file is left as you wrote it.

Not in `library.json`: PlatformIO gives the `build_flags` of a `library.json` to the library's own files and to nothing else, so your code, which includes the library's header, would not see the define, and the two would not agree on what the header declares.

Every install writes the lines again from the library's new `installer.yml`, and an uninstall takes them out, with the section the installer added, so `platformio.ini` is back to the byte it was.

### Frameworks and platforms

PlatformIO leaves a library out of any build whose framework or platform the library does not list, without a word, and your `#include` then simply finds nothing. So before anything is written, the installer reads every environment in `platformio.ini` and names any the library will not build in:

```
Requirements
  check   [env:esp32] builds with espidf, which example does not list, so PlatformIO leaves it out of that build
          example lists: arduino.
```

It is a warning and nothing more. The library still goes in, for the environments it does build in.

### A library that needs another

What a library needs goes into `lib` too, beside it, and installs first. In `lib` every library finds the others' headers, so nothing else is needed. One already there at a version that will do is left alone. Everything is fetched before anything is installed, so when a library cannot be had, nothing is changed.

A library from the [PlatformIO Registry](https://registry.platformio.org), such as ArduinoJson, is a different thing: the library lists it, the installer writes it into the library's `library.json`, and PlatformIO installs it by itself at the next build.

### Settings

A library's settings are in its configuration header, between `USER CODE BEGIN` and `USER CODE END`:

```c
/* USER CODE BEGIN EXAMPLE_CONFIGURATION */
#define EXAMPLE_PERIOD_MS           250U
/* USER CODE END EXAMPLE_CONFIGURATION */
```

Change them there. Every install and update keeps what is between those lines. The library is in your project's `lib`, so they are your project's settings, for every environment it builds.

### What you see

A first install from GitHub, of a library that needs I2C and a define:

```
Fetching owner/example ...

example 1.2.0
Driver for the X chip
driver / storage

Requirements
  note    EXAMPLE_FAST goes into build_flags in platformio.ini
  note    Needs I2C, 400 kHz
          Set it up in your code.

Folder to install example into [lib/example]:

Files
  written lib/example/src/example.h
  written lib/example/src/example_config.h
  written lib/example/src/example.c

Project
  updated library.json  Wrote example's library.json, which PlatformIO builds it by.
  updated platformio.ini  Added example's defines to platformio.ini, for every environment.
          backup: platformio.ini.20261017-091500.bak

Done. #include "example.h" and you are away.
```

### What to install

The argument can be any of these, and you can give several at once:

| You have | You type |
|---|---|
| Nothing yet, and internet | `pio-installer owner/example` |
| The library's GitHub address | `pio-installer https://github.com/owner/example` |
| The zip from GitHub's **Download ZIP** | `pio-installer D:/Downloads/example-main.zip` |
| That zip unpacked, anywhere on disk | `pio-installer D:/Downloads/example-main` |

A bare name with no owner, like `example`, is a NimaLTD library, `nimaltd/example` on GitHub, unless a folder of that name exists where you run it, in which case the folder is used. A path that does not exist is reported as missing rather than looked up on GitHub.

### Options

| Option | What it does |
|---|---|
| `--project D:/projects/blink` | The project's folder, the one holding `platformio.ini`, when you are not running from it |
| `--dir lib/example2` | The folder to install into, for one library. Asked for when not given, with `lib/` and the library's name as the answer if you just press Enter, or the folder it is already in |
| `--ref v2.0.0` | A tag, a branch or a commit to take from GitHub. When not given, `main`, or `master` for a repository that has no `main` |
| `--key github_pat_...` | A GitHub token, for a library in a private repository. See [A private repository](#a-private-repository) |
| `--uninstall example` | Take the library out. See [Uninstalling a library](#uninstalling-a-library) |
| `--with uptime` | Take this part of the library without being asked. Give it once for each part |
| `--without uptime` | Leave this part out, or take it out of a library already installed |
| `--version` | Show which version of the installer you have, and do nothing else |

In a script, where nobody can answer, every question takes the answer offered.

### Updating a library

Run the same command again. Every file of the library is replaced, so an update updates, and `library.json` and the lines in `platformio.ini` are written again from the new `installer.yml`. What you wrote between `USER CODE BEGIN` and `USER CODE END` is kept. Outside those lines, the next install replaces it, and when that would lose something of yours the file is saved beside it first, as a `.bak`. `platformio.ini` is saved the same way, before each change, as `platformio.ini.<date>-<time>.bak`.

The record of what is installed, and where, is `.pio-installer.json`, beside `platformio.ini`.

### Uninstalling a library

```bash
pio-installer --uninstall example
```

Its files go, its `library.json`, and its lines in `platformio.ini`. What was yours is saved before it goes, as a `.bak` beside it: a configuration header with your settings in it, or any file of the library you changed by hand. A file you put in the library's folder yourself is left where it is, and the folder with it.

A library another one needs stays, and the installer says which needs it. One that came in only because the library needed it stays too, and the installer says how to take it out.

### Without internet

On a machine that has internet, `pip download pio-installer` saves one file, the installer, which needs nothing else. Download the library too, from the green **Code** button, **Download ZIP**. Then, on the machine with no internet:

```bash
pip install pio_installer-1.0.0-py3-none-any.whl
pio-installer D:/Downloads/example-main.zip
```

If the library needs another, give that zip on the same line. A library that needs one from the PlatformIO Registry needs internet for the first build, when PlatformIO fetches it. Behind a proxy, set `HTTPS_PROXY` to its address.

### A private repository

A library in a private repository installs the same way, given a GitHub token that can read it. Make one once:

1. Open [github.com/settings/personal-access-tokens](https://github.com/settings/personal-access-tokens) and click **Generate new token**.
2. Give it a name and an expiry. Under **Resource owner**, pick the account or the organisation that owns the repository.
3. Under **Repository access**, choose **Only select repositories** and pick the library's repository.
4. Under **Permissions**, set **Contents** to **Read-only**:
   - Older layout: open **Repository permissions** and change **Contents** from **No access** to **Read-only**.
   - Newer layout: click **+ Add permissions**, tick **Contents**, then set its access to **Read-only**.

   **Metadata** comes with it by itself. Contents is the one that matters: without it the token can see the repository but not read a file of it.
5. Click **Generate token**, and copy it. GitHub shows it only once.

Then give it with `--key`:

```bash
pio-installer owner/example --key github_pat_...
```

Or put it in `GITHUB_TOKEN` once, and install by name as usual. That keeps it out of your shell's history, where `--key` leaves it:

**Windows, PowerShell:**

```powershell
$env:GITHUB_TOKEN = "github_pat_..."
pio-installer owner/example
```

**Windows, Command Prompt:**

```bat
set GITHUB_TOKEN=github_pat_...
pio-installer owner/example
```

**Linux and macOS:**

```bash
export GITHUB_TOKEN=github_pat_...
pio-installer owner/example
```

`--key` comes first when both are there. `GH_TOKEN` works as well, and if you use the `gh` command, `gh auth token` prints the token you are signed in with. Whichever way it comes, the token is sent to GitHub and nowhere else.

When the token cannot read the library, the installer says which of these it is:

- **It can see the repository, but cannot read its files.** The token has no Contents permission, only Metadata. Edit the token, and its value stays the same, so the command you ran keeps working: open the tokens page, click the token's name, click **Edit**, set Contents to **Read-only** as in step 4, and click **Update** at the bottom of the page. Then run the same command again.
- **It cannot see the repository.** The repository is not in the token's Repository access. Edit the token as above and add it.
- **GitHub did not accept the token.** It has expired, been revoked, or was copied with a character missing. Make a new one.

A repository of an organisation can need one more step: an organisation that asks for fine-grained tokens to be approved shows the token nothing of its repositories until an owner of the organisation approves it, under its settings, **Personal access tokens**, **Pending requests**.

---

---

## For someone writing a library

Put an `installer.yml` at the root of the repository. Any library can have one, whoever wrote it, and the one file serves pio-installer and the other installers alike: each reads its own keys and leaves the others' alone.

Every key pio-installer reads is below, each with what it does. Only `name` and `files` are required; leave out what your library does not need. For a working one to copy, see [pio-installer-example](https://github.com/nimaltd/pio-installer-example).

```yaml
name: example                      # the library's name, and its folder in lib/
description: Driver for the X chip # one line: shown while installing, and in library.json
repository: https://github.com/owner/example  # where it comes from; its owner is the author
license: Apache-2.0                # the licence's SPDX name
version: 1.0.0                     # only when the first header has no @version tag

kind: driver                       # driver, middleware, rtos, protocol, filesystem,
                                   # utility or bsp: library.json's keywords
category: storage                  # sensor, storage, display, communication, wireless,
                                   # rtos, timing, power, input, math or system
provides: []                       # what it gives other libraries: [rtos] for an RTOS

requires:
  pio_installer: 1.0.0             # the oldest pio-installer that reads this file
  libraries:                       # other libraries, installed first into lib/
    - osal >= 1.0.0                # no owner means nimaltd
    - owner/lib                    # anyone else's, as owner/name
  peripherals:                     # hardware it uses, named to the user
    - type: i2c                    # what it is
      note: 400 kHz                # how to set it up

install:
  layout: mirror                   # mirror keeps the repository's folders,
                                   # flat (the default) puts every file at the top
  include_dirs: [src, src/port]    # include folders, only when the guess is wrong:
                                   # the first is library.json's includeDir
  defines:                         # build_flags in platformio.ini, for every environment
    - EXAMPLE_FAST                 # NAME, or NAME=value

files:
  headers:                         # .h files; the first is the one to #include
    - src/example.h
    - src/example_config.h         # its settings, in USER CODE lines kept on update
  sources:                         # .c and .cpp files, the only ones PlatformIO builds
    - src/example.c
    - from: src/port/spi.c         # a file that goes somewhere of its own,
      to: src/port/spi.c           # whatever the layout says

options:                           # parts the user chooses at install
  uptime:                          # the name typed after --with
    description: Uptime in hours, minutes and seconds  # the question asked
    libraries: []                  # libraries this part needs, installed first
    files:                         # its files, written like files above
      sources:
        - src/example_uptime.c

extras:                            # copied as they are, never compiled
  - LICENSE.md                     # LICENSE.md and NOTICE are the default,
  - NOTICE                         # so leave this out if that is all
  - README.md

pio:                               # read by pio-installer only, for library.json
  frameworks: [arduino, espidf]    # the frameworks it builds with, as platformio.ini
                                   # names them; any, "*", when left out
  platforms: [espressif32]         # the platforms it builds for; any, "*", when left out
  dependencies:                    # PlatformIO Registry libraries it needs, as
    - bblanchon/ArduinoJson@^7     # owner/name, with @version when one is needed.
                                   # PlatformIO installs them by itself
```

Keys only the other installers read, such as `requires.installer`, `zephyr`, `esp32` and `arduino`, can stay in the same file. This installer skips them.

Leave `version` out. The installer reads the version from the `@version` tag in the file comment of the first header listed, so it is written in the code and nowhere else.

`requires.pio_installer` is the oldest pio-installer that reads the file correctly. It is checked before anything else in the file is read, so an older installer stops with a message saying to update, rather than read the file wrongly. Write it as three numbers, `1.0.0`: unquoted, YAML reads `1.10` as the decimal number `1.1`, and that is refused.

In YAML, `*` alone starts something else, so write any as `"*"` or `["*"]`, or leave the key out.

### What PlatformIO needs of a library

- **The header to include first in `headers`.** `library.json` names one include folder, the one the first header listed is in, unless `install.include_dirs` names the folders. A header in any other folder is found too: the installer adds that folder to `library.json` as `-I`, which PlatformIO gives the library and your project alike.
- **`extern "C"` in every header of C code**, when a project in C++ may use it, as one with the Arduino framework does. Without it the linker cannot find a function of a `.c` file.
- **Settings in a configuration header**, between `USER CODE` lines the installer keeps.
- **A define in `install.defines` only when the whole build needs it.** It goes into every environment of the project. A setting that only the library reads belongs in its configuration header.
- **`frameworks` and `platforms` that are true.** Listing too few hides the library from a build that could use it, and the installer warns about it; listing too many lets a build try and fail.

A library made for PlatformIO that ships its own `library.json`, listed under `extras` or `files` so it is installed, keeps it: the installer writes one only for a library that has none.

---

## Running the tests

The shared core, [core-installer](https://github.com/nimaltd/core-installer), is a git submodule in `src/core`, so clone with it:

```bash
git clone --recursive https://github.com/nimaltd/pio-installer.git
```

In a clone made without `--recursive`, `git submodule update --init` fetches it. Then:

```bash
python test/run_tests.py
```

CI also installs a small library from `test/e2e/`, and the one it needs, with the installer it just built, into a project with two environments: one with `build_flags` of its own, and one without. It changes the library's setting and installs again, builds both environments with PlatformIO on the native platform, and runs them: the library's header stops the build when its define did not arrive, and the program prints a number made from the setting the update had to keep. Then it takes the library out, and checks `platformio.ini` is back to the byte it was. So every release is known to work with real PlatformIO.

---

## Support

I write these tools and libraries in my own time and give them away, because good tools should be easy to get. If this one saved you an afternoon, there are two things that genuinely help:

**Star the repo.** It costs you one click, it helps other engineers find the tool, and it is the main reason I keep going.

**[Buy me a coffee on Ko-fi](https://ko-fi.com/nimaltd).** Any amount is a real motivation to keep writing, documenting and maintaining this work.

[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=for-the-badge&logo=github)](https://github.com/NimaLTD)
[![YouTube](https://img.shields.io/badge/YouTube-Subscribe-red?style=for-the-badge&logo=youtube)](https://youtube.com/@nimaltd)
[![Instagram](https://img.shields.io/badge/Instagram-Follow-purple?style=for-the-badge&logo=instagram)](https://instagram.com/github.nimaltd)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=for-the-badge&logo=linkedin)](https://linkedin.com/in/nimaltd)
[![Email](https://img.shields.io/badge/Email-Contact-red?style=for-the-badge&logo=gmail)](mailto:nima.askari@gmail.com)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support-orange?style=for-the-badge&logo=ko-fi)](https://ko-fi.com/nimaltd)

---

## License

Apache License 2.0. See [LICENSE](https://github.com/nimaltd/pio-installer/blob/main/LICENSE).
