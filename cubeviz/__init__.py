# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
This is an Astropy affiliated package.
"""

# Affiliated packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._astropy_init import *
# ----------------------------------------------------------------------------

# This ensures that all custom toolbar modes are imported so that they are
# registered by @viewer_tool and are available for use by CubeViz.
from .toolbar_modes import *
