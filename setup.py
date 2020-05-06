from distutils.dir_util import mkpath, remove_tree
from distutils import log
import os
from setuptools import setup, find_packages, Extension, Command
from setuptools.command import build_py
from setuptools.command.egg_info import egg_info
import subprocess
import sys

PY = sys.executable


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
        self.run_command('build_static')
        build_py.build_py.run(self)


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
        from io import BytesIO
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
                f = BytesIO()
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
            # may revisit this later; since meson is Python, there's probably
            # a better way but for now this works.
            # Doing this here because we have easy access to OTS version to
            # replace in the meson build.
            if not self.dry_run:
                with open("src/ots/meson.build", 'w') as f:
                    f.write(custom_meson.replace("<OTS_VER>", self.version))


custom_meson = f"""
project('ots', 'c', 'cpp',
  version: '<OTS_VER>',
  default_options : [
      'cpp_std=c++11',
      'default_library=static',
      'b_staticpic=True'],
)

cxx = meson.get_compiler('cpp')

conf = configuration_data()
conf.set_quoted('PACKAGE', meson.project_name())
conf.set_quoted('VERSION', meson.project_version())

if get_option('debug')
  conf.set('OTS_DEBUG', 1)
endif

if get_option('graphite')
  conf.set('OTS_GRAPHITE', 1)
endif

freetype = dependency('freetype2', required: false)
if freetype.found()
  conf.set('HAVE_FREETYPE', 1)
endif

coretext = dependency('appleframeworks', modules: 'applicationservices',
                      required: false)
if coretext.found()
  conf.set('HAVE_CORETEXT', 1)
endif

gdi32 = cxx.find_library('gdi32', required: false)
if gdi32.found()
  conf.set('HAVE_WIN32', 1)
endif


configure_file(output: 'config.h',
               configuration: conf)


brotli_includes = ['third_party/brotli/c/include']
libbrotli = library('brotli',
  'third_party/brotli/c/common/constants.h',
  'third_party/brotli/c/common/dictionary.c',
  'third_party/brotli/c/common/dictionary.h',
  'third_party/brotli/c/common/transform.c',
  'third_party/brotli/c/common/transform.h',
  'third_party/brotli/c/common/version.h',
  'third_party/brotli/c/dec/bit_reader.c',
  'third_party/brotli/c/dec/bit_reader.h',
  'third_party/brotli/c/dec/decode.c',
  'third_party/brotli/c/dec/huffman.c',
  'third_party/brotli/c/dec/huffman.h',
  'third_party/brotli/c/dec/prefix.h',
  'third_party/brotli/c/dec/state.c',
  'third_party/brotli/c/dec/state.h',
  'third_party/brotli/c/include/brotli/decode.h',
  'third_party/brotli/c/include/brotli/port.h',
  'third_party/brotli/c/include/brotli/types.h',
  include_directories: include_directories(brotli_includes),
)


woff2_includes = ['third_party/brotli/c/include', 'third_party/woff2/include']
libwoff2 = library('woff2',
  'third_party/woff2/include/woff2/decode.h',
  'third_party/woff2/include/woff2/output.h',
  'third_party/woff2/src/buffer.h',
  'third_party/woff2/src/port.h',
  'third_party/woff2/src/round.h',
  'third_party/woff2/src/store_bytes.h',
  'third_party/woff2/src/table_tags.cc',
  'third_party/woff2/src/table_tags.h',
  'third_party/woff2/src/variable_length.cc',
  'third_party/woff2/src/variable_length.h',
  'third_party/woff2/src/woff2_common.cc',
  'third_party/woff2/src/woff2_common.h',
  'third_party/woff2/src/woff2_dec.cc',
  'third_party/woff2/src/woff2_out.cc',
  include_directories: include_directories(woff2_includes),
)


ots_includes = [
  'include',
  'third_party/woff2/include',
]

ots_sources = [
  'src/avar.cc',
  'src/avar.h',
  'src/cff.cc',
  'src/cff.h',
  'src/cff_charstring.cc',
  'src/cff_charstring.h',
  'src/cmap.cc',
  'src/cmap.h',
  'src/cvar.cc',
  'src/cvar.h',
  'src/cvt.cc',
  'src/cvt.h',
  'src/fpgm.cc',
  'src/fpgm.h',
  'src/fvar.cc',
  'src/fvar.h',
  'src/gasp.cc',
  'src/gasp.h',
  'src/gdef.cc',
  'src/gdef.h',
  'src/glyf.cc',
  'src/glyf.h',
  'src/gpos.cc',
  'src/gpos.h',
  'src/gsub.cc',
  'src/gsub.h',
  'src/gvar.cc',
  'src/gvar.h',
  'src/hdmx.cc',
  'src/hdmx.h',
  'src/head.cc',
  'src/head.h',
  'src/hhea.cc',
  'src/hhea.h',
  'src/hmtx.cc',
  'src/hmtx.h',
  'src/hvar.cc',
  'src/hvar.h',
  'src/kern.cc',
  'src/kern.h',
  'src/layout.cc',
  'src/layout.h',
  'src/loca.cc',
  'src/loca.h',
  'src/ltsh.cc',
  'src/ltsh.h',
  'src/math.cc',
  'src/math_.h',
  'src/maxp.cc',
  'src/maxp.h',
  'src/metrics.cc',
  'src/metrics.h',
  'src/mvar.cc',
  'src/mvar.h',
  'src/name.cc',
  'src/name.h',
  'src/os2.cc',
  'src/os2.h',
  'src/ots.cc',
  'src/ots.h',
  'src/post.cc',
  'src/post.h',
  'src/prep.cc',
  'src/prep.h',
  'src/stat.cc',
  'src/stat.h',
  'src/variations.cc',
  'src/variations.h',
  'src/vdmx.cc',
  'src/vdmx.h',
  'src/vhea.cc',
  'src/vhea.h',
  'src/vmtx.cc',
  'src/vmtx.h',
  'src/vorg.cc',
  'src/vorg.h',
  'src/vvar.cc',
  'src/vvar.h',
]

ots_libs = [libbrotli, libwoff2]

if get_option('graphite')
  ots_includes += ['third_party/lz4/lib']
  ots_sources += [
    'src/feat.cc',
    'src/feat.h',
    'src/glat.cc',
    'src/glat.h',
    'src/gloc.cc',
    'src/gloc.h',
    'src/graphite.h',
    'src/sile.h',
    'src/sile.cc',
    'src/silf.h',
    'src/silf.cc',
    'src/sill.h',
    'src/sill.cc',
  ]
  liblz4 = library('lz4',
    'third_party/lz4/lib/lz4.c',
    'third_party/lz4/lib/lz4.h',
  )
  ots_libs += [liblz4]
endif

zlib = dependency('zlib', fallback : ['zlib', 'zlib_dep'])

libots = library('ots',
  ots_sources,
  include_directories: include_directories(ots_includes),
  link_with: ots_libs,
  cpp_args : '-DHAVE_CONFIG_H',
  dependencies: zlib,
)
"""


custom_commands = {
    'build_py': BuildPy,
    'build_static': BuildStaticLibs,
    'download': Download,
    'egg_info': CustomEggInfo
}

pyots_mod = Extension(
    name='_pyots',
    extra_compile_args=['-std=c++11'],
    extra_objects=[
        'build/meson/libots.a',
        'build/meson/libwoff2.a',
        'build/meson/libbrotli.a',
        'build/meson/liblz4.a'],
    libraries=['z'],
    include_dirs=['build/meson/',
                  'src/ots/include',
                  'src/ots/include/src',
                  'src/ots/third_party/brotli/c/include',
                  'src/ots/third_party/lz4/lib',
                  'src/ots/third_party/woff2/include/woff2'],
    sources=['src/_pyots/bindings.cpp'],
)

setup(
    author='Josh Hadley',
    author_email='johadley@adobe.com',
    cmdclass=custom_commands,
    description='Python wrapper for ot-sanitizer',
    ext_modules=[pyots_mod],
    name='pyots',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    version='0.1.1',
)
