import io
import os
import re
from setuptools import setup, find_packages, Extension, Command
from setuptools.command import build_py
from setuptools.command.egg_info import egg_info
from distutils.dir_util import mkpath, remove_tree
from distutils import log
import subprocess
import sys

PY = sys.executable
inc_dirs = []


def _extra_objs():
    """
    Generator for extra_objects of Extension build.
    """
    ext_objs = ['build/meson/libots.a']

    # for subproject libs we dynamically scan since versions can vary
    subprojpath = os.path.join("build", "meson", "subprojects")
    subprojects = os.listdir(subprojpath)
    for d in subprojects:
        if d.startswith("woff2-"):
            ext_objs.append(os.path.join(subprojpath, d, "libwoff2_common.a"))
            ext_objs.append(os.path.join(subprojpath, d, "libwoff2_decoder.a"))
        if d.startswith("brotli-"):
            ext_objs.append(os.path.join(subprojpath, d, "libbrotli_common.a"))
            ext_objs.append(os.path.join(subprojpath, d, "libbrotli_decoder.a"))  # noqa: E501
        if d.startswith("lz4-"):
            ext_objs.append(os.path.join(subprojpath, d, "contrib", "meson", "meson", "lib", "liblz4.a"))  # noqa: E501

    for x in ext_objs:
        print(f"DBG ext_objs {x}")
        yield x


def _include_dirs():
    """
    Generator for include_dirs of Extension build.
    """
    inc_dirs = ['build/meson/', 'src/ots/include']

    # for subproject include dirs we dynamically scan since versions can vary
    subprojpath = os.path.join("src", "ots", "subprojects")
    subprojects = os.listdir(subprojpath)
    for d in subprojects:
        if d.startswith("woff2-"):
            inc_dirs.append(os.path.join(subprojpath, d, "include"))
        if d.startswith("brotli-"):
            inc_dirs.append(os.path.join(subprojpath, d, "c", "include"))
        if d.startswith("lz4-"):
            inc_dirs.append(os.path.join(subprojpath, d, "lib"))

    for x in inc_dirs:
        print(f"DBG inc_dirs {x}")
        yield x


class BuildStaticLibs(Command):
    """
    Custom command to run build.py script prior to building Extension
    """
    description = 'Build ots static libs from source with meson/ninja'
    user_options = []

    def run(self):
        cmd = [PY, "build.py"]
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
        global inc_dirs
        self.run_command('build_static')
        build_py.build_py.run(self)
        inc_dirs += _include_dirs()
        print("\n\n", inc_dirs, "\n\n")


class CustomEggInfo(egg_info):

    def run(self):
        # make sure the ots source is downloaded before creating sdist manifest
        self.run_command("download")
        egg_info.run(self)


class Download(Command):

    user_options = [
        ("version=", None, "ots source version number to download"),
        ("sha256=", None, "expected SHA-256 hash of the source archive"),
        ("download-dir=",
         "d",
         "where to unpack the 'ots' dir (default: src)"),
        ("clean", None, "remove existing directory before downloading"),
    ]
    boolean_options = ["clean"]

    URL_TEMPLATE = (
        "https://github.com/khaledhosny/ots/releases/download/"
        "v{version}/ots-{version}.tar.xz"
    )

    def initialize_options(self):
        self.version = None
        self.download_dir = None
        self.clean = False
        self.sha256 = None

    def finalize_options(self):
        if self.version is None:
            from distutils.errors import DistutilsSetupError

            raise DistutilsSetupError("must specify --version to download")

        if self.sha256 is None:
            from distutils.errors import DistutilsSetupError

            raise DistutilsSetupError(
                "must specify --sha256 of downloaded file")

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
            remove_tree(output_dir, verbose=self.verbose, dry_run=self.dry_run)

        if os.path.isdir(output_dir):
            log.info("{} was already downloaded".format(output_dir))
        else:
            archive_name = self.url.rsplit("/", 1)[-1]

            mkpath(self.download_dir,
                   verbose=self.verbose,
                   dry_run=self.dry_run)

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
                from distutils.errors import DistutilsSetupError

                raise DistutilsSetupError(
                    "invalid SHA-256 checksum:\n"
                    "actual:   {}\n"
                    "expected: {}".format(actual_sha256, self.sha256)
                )

            log.info("unarchiving {} to {}".format(archive_name, output_dir))
            if not self.dry_run:
                with lzma.open(f) as xz:
                    with tarfile.open(fileobj=xz) as tar:
                        filelist = tar.getmembers()
                        first = filelist[0]
                        if not (first.isdir() and first.name.startswith("ots")):  # noqa: E501
                            from distutils.errors import DistutilsSetupError

                            raise DistutilsSetupError(
                                "The downloaded archive is not recognized as "
                                "a valid ots source tarball"
                            )
                        # strip the root 'ots-X.X.X' directory first
                        rootdir = first.name + "/"
                        to_extract = []
                        for member in filelist[1:]:
                            if member.name.startswith(rootdir):
                                member.name = member.name[len(rootdir):]
                                to_extract.append(member)
                        tar.extractall(output_dir, members=to_extract)

            log.info("writing custom meson.build")

            # updates to meson.build for custom dylib build
            if not self.dry_run:
                with open("src/ots/meson.build", 'r') as f:
                    meson = f.read()

                    # back up original
                    with open("src/ots/meson.build.orig", 'w') as f_out:
                        f_out.write(meson)

                # update default_options
                meson = re.sub(
                    r"default_options : \[(.+)],",
                    r"default_options : [\1, 'b_staticpic=True'],",
                    meson,
                )
                # remove unused ('executable('ots-sanitize' and all after)
                meson = re.sub(
                    r"executable\('ots-sanitize'(.+)",
                    '',
                    meson,
                    flags=re.MULTILINE | re.DOTALL,
                )

                # save it
                with open("src/ots/meson.build", 'w') as f:
                    f.write(meson)


custom_commands = {
    'build_py': BuildPy,
    'build_static': BuildStaticLibs,
    'download': Download,
    'egg_info': CustomEggInfo
}

pyots_mod = Extension(
    name='_pyots',
    extra_compile_args=['-std=c++11'],
    extra_objects=_extra_objs(),
    libraries=['z'],
    include_dirs=inc_dirs,
    sources=['src/_pyots/bindings.cpp'],
)

with io.open("README.md", encoding="utf-8") as readme:
    long_description = readme.read()

classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Testing',
    'License :: OSI Approved :: BSD License',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Operating System :: MacOS :: MacOS X',
    'Operating System :: POSIX :: Linux',
]

setup(
    author='Adobe Type team & friends',
    author_email='afdko@adobe.com',
    cmdclass=custom_commands,
    classifiers=classifiers,
    description='Python wrapper for ot-sanitizer',
    ext_modules=[pyots_mod],
    long_description=long_description,
    long_description_content_type='text/markdown',
    name='pyots',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    python_requires='>=3.6',
    url='https://github.com/adobe-type-tools/pyots',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    zip_safe=False,
)
