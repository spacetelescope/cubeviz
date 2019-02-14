# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
This is an Astropy affiliated package.
"""

__minimum_python_version__ = "3.6"

# Affiliated packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._internal_init import *
# ----------------------------------------------------------------------------

from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = "unknown"


# This *must* occur before any imports from glue. It prevents the "python must
# be installed as a framework" error that occurs on OSX. Since we now
# explicitly depend on PyQt5, we use it as the mpl backend.
import matplotlib as mpl
mpl.use('Qt5Agg')

import astropy.units as units
from .flux_equivalences import CustomFluxEquivalences
# We override the units.equivalencies.spectral_density function with
# CustomFluxEquivalences before the program starts. We expect all libraries
# to access CustomFluxEquivalences when calling for units.equivalencies.spectral_density
units.equivalencies.spectral_density = CustomFluxEquivalences(units.equivalencies.spectral_density)
units.spectral_density = units.equivalencies.spectral_density

from . import keyboard_shortcuts
