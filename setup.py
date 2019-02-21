#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst

import glob
import os
import sys

import ah_bootstrap
from setuptools import setup

# A dirty hack to get around some early import/configurations ambiguities
import builtins
builtins._CUBEVIZ_SETUP_ = True

from astropy_helpers.setup_helpers import (register_commands, get_debug_option,
                                           get_package_info)
from astropy_helpers.git_helpers import get_git_devstr
from astropy_helpers.version_helpers import generate_version_py

# Get some values from the setup.cfg
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

conf = ConfigParser()
conf.read(['setup.cfg'])
metadata = dict(conf.items('metadata'))

PACKAGENAME = metadata.get('package_name', 'cubeviz')

# VERSION should be PEP440 compatible (http://www.python.org/dev/peps/pep-0440)
VERSION = metadata.get('version', '0.0.dev0')

# Indicates if this version is a release version
RELEASE = 'dev' not in VERSION

if not RELEASE:
    VERSION += get_git_devstr(False)

# Populate the dict of setup command overrides; this should be done before
# invoking any other functionality from distutils since it can potentially
# modify distutils' behavior.
cmdclassd = register_commands(PACKAGENAME, VERSION, RELEASE)

# Freeze build information in version.py
generate_version_py(PACKAGENAME, VERSION, RELEASE,
                    get_debug_option(PACKAGENAME))

setup(name=PACKAGENAME,
      version=VERSION,
      cmdclass=cmdclassd,
      zip_safe=False,
      use_2to3=False,
)
