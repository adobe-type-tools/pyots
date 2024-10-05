# pyots (PYthon OT Sanitizer)

[![Run Tests](https://github.com/adobe-type-tools/pyots/actions/workflows/run_tests.yml/badge.svg)](https://github.com/adobe-type-tools/pyots/actions/workflows/run_tests.yml) [![Build Python Wheels](https://github.com/adobe-type-tools/pyots/actions/workflows/release.yml/badge.svg)](https://github.com/adobe-type-tools/pyots/actions/workflows/release.yml)

![PyPI](https://img.shields.io/pypi/v/pyots) [![PyPI](https://img.shields.io/pypi/pyversions/pyots)](https://pypi.org/project/pyots/)

![macOS](https://img.shields.io/badge/-macOS-lightgrey) ![ubuntu](https://img.shields.io/badge/-ubuntu-lightgrey)

Python wrapper for [OpenType Sanitizer](https://github.com/khaledhosny/ots), also known as just "OTS". It is similar to and partially based on [ots-python](https://github.com/googlefonts/ots-python), but builds OTS as a Python C Extension (instead of as an executable and calling through `subprocess` as ots-python does).

**NOTE:** Although this package is similar to **ots-python**, it is _not_ a drop-in replacement for it, as the Python API is different.

## Requirements
The project builds `pip`-installable wheels for Python 3.9, 3.10, 3.11, or 3.12 under Mac or Linux. It is possible this project will build and run with other Pythons and other operating systems, but it has only been tested with the listed configurations.

## Installation with `pip`
If you just want to _use_ `pyots`, you can simply run `python -m pip install -U pyots` (in one of the supported platforms/Python versions) which will install pre-built, compiled, ready-to-use Python wheels. Then you can skip down to the [Use](#Use) section.

## Installation/setup for developing `pyots`
If you'd like to tinker with the `pyots` code, you will want to get your local setup ready:
 - clone this repo
 - run `python setup.py download` to download the OTS source (which is _not included_ in this project). You can modify the `version` value in [`setup.cfg`](./setup.cfg) under `[download]` to specify a different version of OTS. You'll also need to change the `sha256` hash value that corresponds to the OTS tar.xz package. Note that this scheme has some limitations: OTS sources older than 8.1.3 might not build correctly since they used different build systems. Also, versions newer than the one specified in this repo might require adjustments in order to build correctly. What can we say, we're dependent on `ots`...
 - to build and install `pyots` after downloading OTS, you can run `python setup.py install` or `python -m pip install .`
 - while iterating changes, you will want to delete the temporary `build` and `src/ots/build` folders.

## Testing
There is a test suite defined for exercising the Python extension. It makes use (and assumes the presence of) the downloaded OTS library source's test font data in `src/ots` so ensure you have run `python setup.py download` and have the `ots` folder under `src`. Invoke the tests with `python -m pytest`.

If you wish to run tests comparing results from `ots-python` against `pyots`, be sure to `python -m pip install opentype-sanitizer` first, otherwise that set of tests will be skipped.

## Use
Simplest case:
```python
import pyots
result = pyots.sanitize('/path/to/font/file.ttf')
```

`result` is an `OTSResult` object with 3 attributes:
 - `sanitized` Boolean indicating whether the file was successfully sanitized
 - `modified` Boolean indicating whether the file was modified* during sanitization
 - `messages` Tuple of message strings generated during sanitization (may be empty)

* **Note:** currently the back-end OTS code can modify fonts that are successfully sanitized, even when no changes are performed. Thus `modified` can sometimes be True when `sanitized` is True. Usually the modification is only to the modification date and related checksums. Thus, it might be possible to devise a better detection of modification, i.e. ignoring `head.modified` and other inconsequential modifications, but that was out-of-scope for this work.

### Example: sanitizing a folder of font files
```python
# sanitize a folder of fonts. Print messages for any that were not successfully sanitized.
import pyots
from pathlib import Path

for filename in Path("src/ots/tests/fonts/good").rglob("*"):
    result = pyots.sanitize(filename.absolute())
    if not result.sanitized:
        print(f'{filename}:\n{", ".join([m for m in result.messages])}')
```

### Options for `sanitize()`
 - Specify keyword `output=<path_to_output_file>` to the `sanitize()` command and the sanitized file will be saved to that location
 - Use `quiet=True` for `sanitize()` to suppress messages
 - Specify `font_index=<index_in_TTC>` when sanitizing a Collection (OTC/TTC) file and you want to sanitize only a particular index within the Collection (otherwise all will be sanitized per OTS's default behavior)
