#!/usr/bin/env python3
"""
Run meson and ninja to build the ots static libs from source.
"""
import sys
from pathlib import Path
import os
import subprocess
import shutil
import errno
import argparse

ROOT = Path(__file__).parent.resolve()
BUILD_ROOT = ROOT / "src" / "ots" / "build"
BUILD_DIR = BUILD_ROOT / "meson"
SRC_DIR = ROOT / "src"
OTS_SRC_DIR = SRC_DIR / "ots"
SUB_DIR = OTS_SRC_DIR / "subprojects"


if 'manylinux' in os.environ.get("AUDITWHEEL_PLAT", ''):
    os.environ["PATH"] += os.pathsep + os.path.dirname(sys.executable)

TOOLS = {
    "meson": os.environ.get("MESON_EXE", "meson"),
    "ninja": os.environ.get("NINJA_EXE", "ninja"),
}

MESON_CMD = [
    TOOLS["meson"],
    "--backend=ninja",
    "--buildtype=release",
    "--strip",
    "--default-library=static",
    "--force-fallback-for=libbrotlidec,liblz4",
    str(BUILD_DIR),
    str(OTS_SRC_DIR),
]

NINJA_CMD = [TOOLS["ninja"], "-C", str(BUILD_DIR)]


class ExecutableNotFound(FileNotFoundError):
    def __init__(self, name, path):
        msg = f"{name} executable not found: '{path}'"
        super().__init__(errno.ENOENT, msg)


def check_tools():
    for name, path in TOOLS.items():
        if shutil.which(path) is None:
            raise ExecutableNotFound(name, path)


def configure(reconfigure=False):
    print(f"build.py: Running {' '.join(MESON_CMD)}")
    if not (BUILD_DIR / "build.ninja").exists():
        subprocess.run(MESON_CMD, check=True, env=os.environ)
    elif reconfigure:
        subprocess.run(MESON_CMD + ["--reconfigure"],
                       check=True,
                       env=os.environ)


def make(*targets, clean=False):
    print(f"build.py: Running {' '.join(NINJA_CMD)}")
    targets = list(targets)
    if clean:
        subprocess.run(NINJA_CMD + ["-t", "clean"] + targets,
                       check=True,
                       env=os.environ)
    subprocess.run(NINJA_CMD + targets, check=True, env=os.environ)


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("targets", nargs="*")
    options = parser.parse_args(args)

    check_tools()

    try:
        configure(reconfigure=options.force)

        make(*options.targets, clean=options.force)
    except subprocess.CalledProcessError as e:
        return e.returncode

    return 0


if __name__ == "__main__":
    sys.exit(main())
