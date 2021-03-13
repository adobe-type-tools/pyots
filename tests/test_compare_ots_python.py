# test_compare_ots-python.py
"""
[optional] tests to compare ots-python to pyots. Will be skipped if ots-python
(opentype-sanitizer/ots) is not installed.
"""

import functools
from pathlib import Path
import timeit

import pytest

import pyots

try:
    import ots
    have_ots = True
except ImportError:
    have_ots = False

ROOT = Path(__file__).parent.parent.resolve()
TEST_FONTS_DIR = ROOT / "src" / "ots" / "tests" / "fonts"


def _get_ots_result(path):
    """
    Sanitize with ots-python and process the result.
    """
    ots_out = ots.sanitize(path, capture_output=True)
    sanitized = b'File sanitized successfully!' in ots_out.stdout
    modified = sanitized
    messages = ots_out.stderr.decode('ascii', errors="ignore")

    return pyots.OTSResult((sanitized, modified, messages))


def _get_pyots_result(path):
    return pyots.sanitize(path)


@pytest.mark.skipif(not have_ots, reason="ots-python not installed")
def test_compare_good():
    tld = TEST_FONTS_DIR / "good"

    for f in tld.iterdir():
        otsp_result = _get_ots_result(f)
        pyots_result = _get_pyots_result(f)
        assert otsp_result.sanitized == pyots_result.sanitized
        assert otsp_result.messages == pyots_result.messages, f"[good] mismatched messages for {f}"


@pytest.mark.skipif(not have_ots, reason="ots-python not available")
def test_compare_bad():
    tld = TEST_FONTS_DIR / "bad"

    for f in tld.iterdir():
        otsp_result = _get_ots_result(f)
        pyots_result = _get_pyots_result(f)
        assert otsp_result.sanitized == pyots_result.sanitized
        assert otsp_result.messages == pyots_result.messages, f"[bad] mismatched messages for {f}"


@pytest.mark.skipif(not have_ots, reason="ots-python not available")
def test_compare_fuzzing():
    tld = TEST_FONTS_DIR / "fuzzing"

    for f in tld.iterdir():
        otsp_result = _get_ots_result(f)
        pyots_result = _get_pyots_result(f)
        assert otsp_result.sanitized == pyots_result.sanitized
        assert otsp_result.messages == pyots_result.messages, f"[fuzzing] mismatched messages for {f}"


def cmp_times():
    """
    This is intentionally not a test_ method and won't be run as part of the test suite.
    If you want to compare, you can do:
        python -c "from tests.test_compare_ots_python import cmp_times; cmp_times()"
    """
    fd = {"pyots": functools.partial(pyots.sanitize, quiet=False),
          "ots-python": functools.partial(ots.sanitize, capture_output=True)}
    rd = {k: 0.0 for k in fd.keys()}

    for name, sanitize_method in fd.items():

        start = timeit.default_timer()
        for subdir in ("good", "bad", "fuzzing"):
            tld = TEST_FONTS_DIR / subdir

            for f in tld.iterdir():
                _ = sanitize_method(f)
        end = timeit.default_timer()

        rd[name] = end - start

    xtime = (rd['ots-python'] / rd['pyots'])
    print(f"[timings] pyots: {rd['pyots']}, ots-python: {rd['ots-python']} ({round(xtime, 1)}x)")
