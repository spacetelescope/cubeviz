# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
This is an Astropy affiliated package.
"""

# Affiliated packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._internal_init import *
# ----------------------------------------------------------------------------

if _CUBEVIZ_SETUP_ is False:
    import astropy.units as units
    from .flux_equivalences import CustomFluxEquivalences
    # We override the units.equivalencies.spectral_density function with
    # CustomFluxEquivalences before the program starts. We expect all libraries
    # to access CustomFluxEquivalences when calling for units.equivalencies.spectral_density
    units.equivalencies.spectral_density = CustomFluxEquivalences(units.equivalencies.spectral_density)
    units.spectral_density = units.equivalencies.spectral_density

    from . import keyboard_shortcuts
