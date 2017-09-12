# Licensed under a 3-clause BSD style license - see LICENSE.rst

from glue.config import data_factory
from glue.core import Data
from astropy.io import fits

import asdf
from asdf.fits_embed import ASDF_EXTENSION_NAME


def _is_jwst_asdf_cube(asdffile):
    meta = asdffile.tree.get('meta')
    if meta is None:
        return False

    instrument = meta.get('instrument')
    if instrument is None:
        return False

    name = instrument.get('name')
    detector = instrument.get('detector')
    if name is None or detector is None:
        return False
    if name != 'NIRSPEC' or not detector.startswith('NRS'):
        return False

    for array_name in ['data', 'dq', 'err']:
        if array_name not in asdffile.tree:
            return False

    return True

def _is_jwst_fits_cube(hdulist):
    pass

def is_jwst_data_cube(filename, **kwargs):
    if filename.endswith('.asdf'):
        try:
            with asdf.open(filename) as af:
                return _is_jwst_asdf_cube(af)
        except ValueError:
            return False
    elif filename.endswith('.fits'):
        try:
            with fits.open(filename) as hdulist:
                # Check whether this is an ASDF file embedded in FITS
                if ASDF_EXTENSION_NAME in hdulist:
                    with asdf.open(hdulist) as af:
                        return _is_jwst_asdf_cube(af)
                # Otherwise treat it as a regular FITS file
                return _is_jwst_fits_cube(hdulist)
        except ValueError:
            return False

    return False

def is_generic_data_cube(filename, **kwargs):
    # It's not clear whether there's a way to detect this automatically
    return False

@data_factory('JWST data cube loader', is_jwst_data_cube, priority=1200)
def read_jwst_data_cube(filename):
    asdffile = asdf.open(filename)
    return Data(
        data=asdffile.tree['data'],
        dq=asdffile.tree['dq'],
        err=asdffile.tree['err'])

@data_factory('Generic data cube loader')
def read_generic_data_cube(filename):
    pass
