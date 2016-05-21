"""setup.py module for PyGeoprocessing"""

import os
import sys

try:
    from setuptools.command.sdist import sdist as _sdist
    from setuptools.command.build_py import build_py as _build_py
    from setuptools.command.build_ext import build_ext
    from setuptools.extension import Extension
except ImportError:
    from distutils.command.sdist import sdist as _sdist
    from distutils.command.build_py import build_py as _build_py
    from distutils.command.build_ext import build_ext
    from distutils.extension import Extension

import natcap.versioner
import numpy

try:
    from setuptools import setup

    # Monkeypatch os.link to prevent hard lnks from being formed.  Useful when
    # running tests across filesystems, like in our test docker containers.
    # Only an issue pre python 2.7.9.
    # See http://bugs.python.org/issue8876
    PY_VERSION = sys.version_info[0:3]
    if PY_VERSION[0] == 2 and PY_VERSION[1] <= 7 and PY_VERSION[2] < 9:
        try:
            del os.link
        except AttributeError:
            pass
except ImportError:
    from distutils.core import setup

# Try to import cython modules, if they don't import assume that Cython is
# not installed and the .c and .cpp files are distributed along with the
# package.
CMDCLASS = {}
try:
    # Overrides the existing build_ext if we can use the cython version.
    from Cython.Distutils import build_ext
    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False

# Defining the command classes for sdist and build_py here so we can access
# the commandclasses in the setup function.
CMDCLASS['sdist'] = _sdist
CMDCLASS['build_py'] = _build_py

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')
LICENSE = open('LICENSE.txt').read()


def no_cythonize(extensions, **_):
    """Replaces instances of .pyx to .c or .cpp depending on the language
        extension."""

    for extension in extensions:
        sources = []
        for sfile in extension.sources:
            path, ext = os.path.splitext(sfile)
            if ext in ('.pyx', '.py'):
                if extension.language == 'c++':
                    ext = '.cpp'
                else:
                    ext = '.c'
                sfile = path + ext
            sources.append(sfile)
        extension.sources[:] = sources
    return extensions

class ExtraCompilerFlagsBuilder(build_ext):
    """
    Subclass of build_ext for adding specific compiler flags required
    for compilation on some platforms.  If we're using GNU compilers, we
    want to statically link libgcc and libstdc++ so that we don't need to
    package shared objects/dynamically linked libraries with this python
    package.

    Trying to statically link these two libraries on unix (mac) will crash, so
    this is only for windows ports of GNU GCC compilers.
    """
    def build_extensions(self):
        compiler_type = self.compiler.compiler_type
        if compiler_type in ['mingw32', 'cygwin']:
            for ext in self.extensions:
                ext.extra_link_args = [
                    '-static-libgcc',
                    '-static-libstdc++',
                ]
        build_ext.build_extensions(self)

CMDCLASS['build_ext'] = ExtraCompilerFlagsBuilder

EXTENSION_LIST = ([
    Extension(
        "pygeoprocessing.geoprocessing_core",
        sources=['pygeoprocessing/geoprocessing_core.pyx'],
        language="c++",
        include_dirs=[numpy.get_include()]),
    Extension(
        "pygeoprocessing.routing.routing_core",
        sources=[
            'pygeoprocessing/routing/routing_core.pyx',
            'pygeoprocessing/routing/routing_core.pxd'],
        language="c++",
        include_dirs=[numpy.get_include()])
    ])

if not USE_CYTHON:
    EXTENSION_LIST = no_cythonize(EXTENSION_LIST)

REQUIREMENTS = [
    'numpy',
    'scipy',
    'shapely',
    'gdal<2.0',
    'natcap.versioner>=0.1.2',
    'nose>=1.0',
    ]

setup(
    name='pygeoprocessing',
    version=natcap.versioner.parse_version(),
    natcap_version=os.path.join('pygeoprocessing', 'version.py'),
    description="Geoprocessing routines for GIS",
    long_description=readme + '\n\n' + history,
    maintainer='Rich Sharp',
    maintainer_email='richsharp@stanford.edu',
    url='http://bitbucket.org/richpsharp/pygeoprocessing',
    packages=[
        'pygeoprocessing',
        'pygeoprocessing.routing',
        'pygeoprocessing.testing',
        'pygeoprocessing.dbfpy',
    ],
    package_dir={'pygeoprocessing': 'pygeoprocessing'},
    include_package_data=True,
    install_requires=REQUIREMENTS,
    include_dirs=[numpy.get_include()],
    setup_requires=['nose>=1.0'],
    cmdclass=CMDCLASS,
    license=LICENSE,
    zip_safe=False,
    keywords='pygeoprocessing',
    classifiers=[
        'Intended Audience :: Developers',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: Scientific/Engineering :: GIS'
    ],
    ext_modules=EXTENSION_LIST,
)
