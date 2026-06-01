import io
import logging
import os
import re
import shutil
from pathlib import Path
from setuptools import setup, Extension, Command
from setuptools.command import build_py
from setuptools.command.build_ext import build_ext
from setuptools.command.egg_info import egg_info
from setuptools.errors import SetupError
import subprocess
import sys

PY = sys.executable

# distutils was removed from the stdlib in Python 3.12 (PEP 632), so use the
# stdlib logging module instead of distutils.log for informational output
logging.basicConfig(format="%(message)s", level=logging.INFO)
log = logging.getLogger("pyots.setup")

# Define paths (previously imported from build_ots.py)
try:
    ROOT = Path(__file__).parent.resolve()
except NameError:
    # Fallback for when __file__ is not defined
    ROOT = Path.cwd()
SRC_DIR = ROOT / "src"
OTS_SRC_DIR = SRC_DIR / "ots"

BUILD_DIR = OTS_SRC_DIR / "build" / "meson"
BUILD_SUB_DIR = BUILD_DIR / "subprojects"
SRC_SUB_DIR = OTS_SRC_DIR / "subprojects"

# TODO: try to make this scheme less fragile/less dependent on hard-coded tags
# to avoid changing it with every new ots release (although it seems like every
# release of ots has something that causes this build to break anyway so it's
# not really that urgent. We just have to adjust every release.
BROTLI_TAG = "1.1.0"
LZ4_TAG = "1.9.4"
WOFF2_TAG = "1.0.2"


IS_WINDOWS = sys.platform == "win32"


def _find_static_lib(search_dir, base):
    """
    Locate a static lib produced by meson regardless of the toolchain's naming
    convention: GCC/Clang produce 'lib<base>.a' while MSVC produces '<base>.lib'
    (and meson may nest it in subdirectories). Returns the resolved Path.
    """
    candidates = [f"lib{base}.a", f"{base}.lib", f"lib{base}.lib", f"{base}.a"]
    for name in candidates:
        # search recursively so we don't depend on meson's exact output layout
        matches = sorted(search_dir.rglob(name))
        if matches:
            return matches[0]
    raise FileNotFoundError(f"could not find static lib for '{base}' under {search_dir} (tried {candidates})")


def _get_extra_objects():
    """
    Create the list of 'extra_ojects' for building the extension. This is done
    in a way to try to be forward-compatible with changes to ots's
    dependencies, but could still break if those dependencies change the names
    of the static libs generated.
    """
    # libots
    xo = [_find_static_lib(BUILD_DIR, "ots")]

    # brotli
    # NOTE: decoder needs to come before common!
    brotli_dir = BUILD_SUB_DIR / f"brotli-{BROTLI_TAG}"
    xo.append(_find_static_lib(brotli_dir, "brotli_decoder"))
    xo.append(_find_static_lib(brotli_dir, "brotli_common"))

    # lz4
    lz4_dir = BUILD_SUB_DIR / f"lz4-{LZ4_TAG}"
    xo.append(_find_static_lib(lz4_dir, "lz4"))

    # zlib -- on Windows there's no system zlib, so meson builds it from the
    # subproject fallback (see build_ots.py) and we link it statically here. On
    # Linux/macOS the system zlib is linked via libraries=["z"] instead.
    if IS_WINDOWS:
        zlib_dirs = sorted(BUILD_SUB_DIR.glob("zlib-*"))
        if not zlib_dirs:
            raise FileNotFoundError(f"could not find zlib build dir under {BUILD_SUB_DIR}")
        # the zlib subproject may name its lib 'z' or 'zlib'
        for base in ("zlib", "z", "zlibstatic"):
            try:
                xo.append(_find_static_lib(zlib_dirs[-1], base))
                break
            except FileNotFoundError:
                continue
        else:
            raise FileNotFoundError(f"could not find zlib static lib under {zlib_dirs[-1]}")

    # woff2 -- skipped for now, building as part of Extension
    # xo.append(BUILD_SUB_DIR / f"woff2-{WOFF2_TAG}" / "libwoff2_decoder.a")
    # xo.append(BUILD_SUB_DIR / f"woff2-{WOFF2_TAG}" / "libwoff2_common.a")

    return [str(p.relative_to(ROOT)) for p in xo]


def _get_include_dirs():
    """
    Create the list of 'include_dirs' for building the Extension.
    """
    ip = [
        BUILD_DIR,
        SRC_DIR / "_pyots",
        OTS_SRC_DIR / "include",
    ]

    # lz4
    ip.append(SRC_SUB_DIR / f"lz4-{LZ4_TAG}" / "lib")

    # brotli
    ip.append(SRC_SUB_DIR / f"brotli-{BROTLI_TAG}" / "c" / "include")

    # woff2
    ip.append(SRC_SUB_DIR / f"woff2-{WOFF2_TAG}" / "include")

    return [str(p.relative_to(ROOT)) for p in ip]


def _get_sources():
    """
    Create the list of 'sources' for building the Extension.
    """
    sp = [
        SRC_DIR / "_pyots" / "bindings.cpp",
    ]

    # woff2 sources
    sp.append(SRC_SUB_DIR / f"woff2-{WOFF2_TAG}" / "src" / "table_tags.cc")
    sp.append(SRC_SUB_DIR / f"woff2-{WOFF2_TAG}" / "src" / "variable_length.cc")  # noqa: E501
    sp.append(SRC_SUB_DIR / f"woff2-{WOFF2_TAG}" / "src" / "woff2_common.cc")
    sp.append(SRC_SUB_DIR / f"woff2-{WOFF2_TAG}" / "src" / "woff2_dec.cc")
    sp.append(SRC_SUB_DIR / f"woff2-{WOFF2_TAG}" / "src" / "woff2_out.cc")

    return [str(p.relative_to(ROOT)) for p in sp]


class BuildStaticLibs(Command):
    """
    Custom command to run build_ots.py script prior to building Extension
    """

    description = "Build ots static libs from source with meson/ninja"
    user_options = []

    def run(self):
        cmd = [PY, "build_ots.py"]
        subprocess.check_call(cmd)

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass


class BuildPy(build_py.build_py):
    """
    Custom python build command. Calls 'build_static' prior to Python build.
    """

    def run(self):
        self.run_command("build_static")
        build_py.build_py.run(self)


class BuildExt(build_ext):
    """
    Custom build_ext that resolves the static libs to link against at build
    time. This must be deferred until here (rather than when the Extension is
    constructed at module load) because the libs don't exist on disk until
    build_ots.py has compiled them.
    """

    def run(self):
        for ext in self.extensions:
            ext.extra_objects = _get_extra_objects()
        build_ext.run(self)


class CustomEggInfo(egg_info):
    def run(self):
        # make sure the ots source is downloaded before creating sdist manifest
        self.run_command("download")
        egg_info.run(self)


class Download(Command):
    user_options = [
        ("version=", None, "ots source version number to download"),
        ("sha256=", None, "expected SHA-256 hash of the source archive"),
        ("download-dir=", "d", "where to unpack the 'ots' dir (default: src)"),
        ("clean", None, "remove existing directory before downloading"),
    ]
    boolean_options = ["clean"]

    URL_TEMPLATE = "https://github.com/khaledhosny/ots/releases/download/v{version}/ots-{version}.tar.xz"

    def initialize_options(self):
        self.version = None
        self.download_dir = None
        self.clean = False
        self.sha256 = None

    def finalize_options(self):
        if self.version is None:
            raise SetupError("must specify --version to download")

        if self.sha256 is None:
            raise SetupError("must specify --sha256 of downloaded file")

        if self.download_dir is None:
            self.download_dir = "src"

        self.url = self.URL_TEMPLATE.format(**vars(self))

    def run(self):
        from urllib.request import urlopen
        import tarfile
        import lzma
        import hashlib

        output_dir = os.path.join(self.download_dir, "ots")
        if self.clean and os.path.isdir(output_dir):
            log.info("removing '{}'".format(output_dir))
            if not self.dry_run:
                shutil.rmtree(output_dir)

        if os.path.isdir(output_dir):
            log.info("{} was already downloaded".format(output_dir))
        else:
            archive_name = self.url.rsplit("/", 1)[-1]

            log.info("creating '{}'".format(self.download_dir))
            if not self.dry_run:
                os.makedirs(self.download_dir, exist_ok=True)

            log.info("downloading {}".format(self.url))
            if not self.dry_run:
                # response is not seekable so we first download *.tar.xz to an
                # in-memory file, and then extract all files to the output_dir
                f = io.BytesIO()
                with urlopen(self.url) as response:
                    f.write(response.read())
                f.seek(0)

                # use hashlib to verify the SHA-256 hash
                actual_sha256 = hashlib.sha256(f.getvalue()).hexdigest()
                if actual_sha256 != self.sha256:
                    raise SetupError(
                        "invalid SHA-256 checksum:\nactual:   {}\nexpected: {}".format(
                            actual_sha256, self.sha256
                        )
                    )

                log.info("unarchiving {} to {}".format(archive_name, output_dir))
                with lzma.open(f) as xz:
                    with tarfile.open(fileobj=xz) as tar:
                        filelist = tar.getmembers()
                        first = filelist[0]
                        if not (first.isdir() and first.name.startswith("ots")):  # noqa: E501
                            raise SetupError(
                                "The downloaded archive is not recognized as a valid ots source tarball"
                            )
                        # strip the root 'ots-X.X.X' directory first
                        rootdir = first.name + "/"
                        to_extract = []
                        for member in filelist[1:]:
                            if member.name.startswith(rootdir):
                                member.name = member.name[len(rootdir) :]
                                to_extract.append(member)
                        tar.extractall(output_dir, members=to_extract)

            log.info("writing custom meson.build")

            # updates to meson.build for custom dylib build
            if not self.dry_run:
                with open("src/ots/meson.build", "r") as f:
                    meson = f.read()

                    # back up original
                    with open("src/ots/meson.build.orig", "w") as f_out:
                        f_out.write(meson)

                # update default_options
                meson = re.sub(
                    r"default_options : \[(.+)],",
                    r"default_options : [\1, 'b_staticpic=True'],",
                    meson,
                )
                # remove unused ('executable('ots-sanitize' and all after)
                meson = re.sub(
                    r"ots_sanitize = executable\('ots-sanitize',(.+)",
                    "",
                    meson,
                    flags=re.MULTILINE | re.DOTALL,
                )

                # save it
                with open("src/ots/meson.build", "w") as f:
                    f.write(meson)


custom_commands = {
    "build_py": BuildPy,
    "build_ext": BuildExt,
    "build_static": BuildStaticLibs,
    "download": Download,
    "egg_info": CustomEggInfo,
}

if IS_WINDOWS:
    # MSVC: no -fPIC, no system zlib (it's linked statically via extra_objects)
    extra_compile_args = ["/std:c++14"]
    libraries = []
else:
    extra_compile_args = ["-fPIC", "-std=c++11"]
    libraries = ["z"]

pyots_mod = Extension(
    name="_pyots",
    libraries=libraries,
    extra_compile_args=extra_compile_args,
    # extra_objects is populated at build time by BuildExt, once build_ots.py has
    # compiled the static libs
    include_dirs=_get_include_dirs(),
    sources=_get_sources(),
)

setup(
    cmdclass=custom_commands,
    ext_modules=[pyots_mod],
)
