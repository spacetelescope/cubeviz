"""The FITS registry for configuring reading of
cube-like data from FITS files.

The registry is an ordered dict where items
added last are tried first.

Users can modify personally by importing this
module and updating fits_registry as below.
"""
from collections import OrderedDict

fits_registry = OrderedDict()
fits_registry.update(
    {'default': {
        'flux': {
            'ext': 0,
            'required': True,
            'wcs': True,
        },
        'error': {
            'ext': 1,
        },
        'mask': {
            'ext': 2,
        },
    }}
)
fits_registry.update(
    {'Keyword Defined': {
        'flux': {
            'ext': 0,
            'ext_card': 'FLUXEXT',
            'wcs': True,
            'required': True,
        },
        'error': {
            'ext': 0,
            'ext_card': 'ERREXT',
        },
        'mask': {
            'ext': 0,
            'ext_card': 'MASKEXT',
        },
    }}
)
fits_registry.update(
    {'CALIFA': {
        'flux': {
            'ext': 'PRIMARY',
            'wcs': True,
            'required': True,
        },
        'error': {
            'ext': 'ERROR',
            'required': True,
        },
        'mask': {
            'ext': 'BADPIX',
            'required': True,
        },
    }}
)
fits_registry.update(
    {'MIRI Engineering': {
        'flux': {
            'ext': 'SCI',
            'wcs': True,
            'required': True,
        },
        'error': {
            'ext': 'UNC',
            'required': True,
        },
        'mask': {
            'ext': 'FLAG',
            'required': True,
        },
    }}
)
fits_registry.update(
    {'NIRSpec Engineering': {
        'flux': {
            'ext': 'DATA',
            'wcs': True,
            'required': True,
        },
        'error': {
            'ext': 'VAR',
            'required': True,
        },
        'mask': {
            'ext': 'QUALITY',
            'required': True,
        },
    }}
)
fits_registry.update(
    {'MUSE': {
        'flux': {
            'ext': 'DATA',
            'wcs': True,
            'required': True,
        },
        'error': {
            'ext': 'STAT',
            'required': True,
        },
        'mask': {
            'ext': 'DQ',
            'required': True,
        },
    }}
)
fits_registry.update(
    {'KMOS': {
        'flux': {
            'ext': '018.DATA',
            'wcs': True,
            'required': True,
            'value': lambda hdu: hdu.data,
        },
        'error': {
            'ext': '018.NOISE',
            'required': True,
            'value': lambda hdu: StdDevUncertainty(hdu.data),
        },
    }}
)
