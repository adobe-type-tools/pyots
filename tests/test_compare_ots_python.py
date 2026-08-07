# test_compare_ots-python.py
"""
[optional] tests to compare ots-python to pyots. Will be skipped if ots-python
(opentype-sanitizer/ots) is not installed.
"""

import configparser
import functools
import timeit
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

import pytest

import pyots

try:
    import ots

    # the pyots wheel bundles a top-level 'ots' package (the OTS source subset),
    # so a bare 'import ots' can succeed even when the opentype-sanitizer package
    # isn't installed; check for its sanitize() to confirm it's the real thing.
    have_ots = hasattr(ots, "sanitize")
except ImportError:
    have_ots = False

ROOT = Path(__file__).parent.parent.resolve()
TEST_FONTS_DIR = ROOT / "src" / "ots" / "tests" / "fonts"


def _ots_versions_match():
    """
    The comparison tests assert byte-identical messages between pyots and
    ots-python, which only holds when both wrap the same OTS version. pyots
    targets the version pinned in setup.cfg, while ots-python's package version
    is its bundled OTS version. Skip the comparison when they differ (e.g. when
    pyots is ahead of the latest opentype-sanitizer release), since the messages
    legitimately diverge on OTS behavior changes.
    """
    if not have_ots:
        return False
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "setup.cfg")
    target = cfg.get("download", "version", fallback=None)
    try:
        installed = pkg_version("opentype-sanitizer")
    except PackageNotFoundError:
        return False
    return target is not None and target == installed


versions_match = _ots_versions_match()
SKIP_REASON = "ots-python not installed or its OTS version differs from pyots's target"


def _get_ots_result(path):
    """
    Sanitize with ots-python and process the result.
    """
    ots_out = ots.sanitize(path, capture_output=True)
    sanitized = b"File sanitized successfully!" in ots_out.stdout
    modified = sanitized
    messages = ots_out.stderr.decode("ascii", errors="ignore")

    return pyots.OTSResult((sanitized, modified, messages))


def _get_pyots_result(path):
    return pyots.sanitize(path)


@pytest.mark.skipif(not versions_match, reason=SKIP_REASON)
def test_compare_good():
    tld = TEST_FONTS_DIR / "good"

    for f in tld.iterdir():
        otsp_result = _get_ots_result(f)
        pyots_result = _get_pyots_result(f)
        assert otsp_result.sanitized == pyots_result.sanitized
        assert otsp_result.messages == pyots_result.messages, f"[good] mismatched messages for {f}"


@pytest.mark.skipif(not versions_match, reason=SKIP_REASON)
def test_compare_bad():
    tld = TEST_FONTS_DIR / "bad"

    for f in tld.iterdir():
        otsp_result = _get_ots_result(f)
        pyots_result = _get_pyots_result(f)
        assert otsp_result.sanitized == pyots_result.sanitized
        assert otsp_result.messages == pyots_result.messages, f"[bad] mismatched messages for {f}"


@pytest.mark.skipif(not versions_match, reason=SKIP_REASON)
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
    fd = {
        "pyots": functools.partial(pyots.sanitize, quiet=False),
        "ots-python": functools.partial(ots.sanitize, capture_output=True),
    }
    rd = {k: 0.0 for k in fd}

    for name, sanitize_method in fd.items():
        start = timeit.default_timer()
        for subdir in ("good", "bad", "fuzzing"):
            tld = TEST_FONTS_DIR / subdir

            for f in tld.iterdir():
                _ = sanitize_method(f)
        end = timeit.default_timer()

        rd[name] = end - start

    xtime = rd["ots-python"] / rd["pyots"]
    print(f"[timings] pyots: {rd['pyots']}, ots-python: {rd['ots-python']} ({round(xtime, 1)}x)")
