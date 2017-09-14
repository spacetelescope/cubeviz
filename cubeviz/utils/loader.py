# Licensed under a 3-clause BSD style license - see LICENSE.rst
from os.path import splitext

from glue.config import data_factory, set_startup_action
from glue.core import Data
from astropy.io import fits

import asdf
from asdf.fits_embed import ASDF_EXTENSION_NAME


def _is_jwst_asdf_cube(asdffile):
    meta = asdffile.tree.get('meta')
    if meta is None:
        return False

    if meta.get('telescope') != 'JWST':
        return False

    if meta.get('model_type') != 'IFUCubeModel':
        return False

    # Other possible checks to use:
    #   meta['exposure']['type'] == 'NRS_IFU' # (for NIRSpec)

    for array_name in ['data', 'dq', 'err']:
        if array_name not in asdffile.tree:
            return False

    return True

def _is_jwst_fits_cube(hdulist):
    if 'PRIMARY' not in hdulist:
        return False

    primary = hdulist['PRIMARY'].header

    if 'TELESCOP' not in primary:
        return False
    if not primary['TELESCOP'].startswith('JWST'):
        return False

    if 'DATAMODL' not in primary:
        return False
    if not primary['DATAMODL'] == 'IFUCubeModel':
        return False

    for extname in ['SCI', 'ERR', 'DQ']:
        if extname not in hdulist:
            return False

    return True

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
    # Maybe it's sufficient to test 'DATAMODL' == 'IFUCubeModel'? Or is that
    # specific to JWST?
    return False

def _load_jwst_asdf(fileobj):
    # fileobj parameter can be either filename or HDUList with ASDF-in-FITS
    asdffile = asdf.open(fileobj)

    dataname = splitext(asdffile.tree['meta']['filename'])[0]
    label = "JWST data cube: {}".format(dataname)
    data = Data(label=label)

    data.add_component(component=asdffile.tree['data'], label='DATA')
    data.add_component(component=asdffile.tree['dq'], label='VAR')
    data.add_component(component=asdffile.tree['err'], label='QUALITY')

    return data

@data_factory('JWST data cube loader', is_jwst_data_cube, priority=1200)
def read_jwst_data_cube(filename):
    # This loads the cubeviz-specific layout
    set_startup_action('cubeviz')

    # Process ASDF files
    if filename.endswith('asdf'):
        return _load_jwst_asdf(filename)
    # Process FITS files (including ASDF-in-FITS)
    else:
        with fits.open(filename) as hdulist:
            if ASDF_EXTENSION_NAME in hdulist:
                return _load_jwst_asdf(hdulist)

            data = hdulist['SCI'].data
            dq = hdulist['DQ'].data
            err = hdulist['ERR'].data
            return Data(data=data, dq=dq, err=err)

@data_factory('Generic data cube loader')
def read_generic_data_cube(filename):
    pass
