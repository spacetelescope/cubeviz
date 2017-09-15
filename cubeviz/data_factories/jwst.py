# Licensed under a 3-clause BSD style license - see LICENSE.rst
from os.path import splitext

from glue.config import data_factory
from glue.core import Data
from glue.core.coordinates import coordinates_from_header
from astropy.io import fits

import asdf
from asdf.fits_embed import ASDF_EXTENSION_NAME

from ..listener import CUBEVIZ_LAYOUT
from ..layout import FLUX, ERROR, MASK


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

    if not primary.get('TELESCOP', '').startswith('JWST'):
        return False

    if not primary.get('DATAMODL', '').startswith('IFUCubeModel'):
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

def _create_data_obj(filename, coords):
    label = "JWST data cube: {}".format(splitext(filename)[0])

    data = Data(label=label)
    data.coords = coords

    # Set metadata indicating specific cubeviz layout to be used
    data.meta[CUBEVIZ_LAYOUT] = 'JWST'

    return data

def _load_jwst_asdf(fileobj, coords):
    # fileobj parameter can be either filename or HDUList with ASDF-in-FITS
    asdffile = asdf.open(fileobj)

    data = _create_data_obj(asdffile.tree['meta']['filename'], coords)

    data.add_component(component=asdffile.tree['data'], label=FLUX)
    data.add_component(component=asdffile.tree['dq'], label=MASK)
    data.add_component(component=asdffile.tree['err'], label=ERROR)

    return data

def _load_jwst_fits(hdulist, coords):
    data = _create_data_obj(hdulist['PRIMARY']['FILENAME'], coords)

    data.add_component(component=hdulist['SCI'].data, label=FLUX)
    data.add_component(component=hdulist['DQ'].data, label=MASK)
    data.add_component(component=hdulist['ERR'].data, label=ERROR)

    return data

@data_factory('JWST data cube loader', is_jwst_data_cube, priority=1200)
def read_jwst_data_cube(filename):
    # Process ASDF files
    if filename.endswith('asdf'):
        # TODO: this is temporary and is not strictly necessary for prototyping
        # at the moment. We're going to have to implement a GWCSCoordinates
        # class that both glue and specviz understand. For now we'll fake it
        # by using the wcs scheme from the FITS 'DATA' HDU below
        data = _load_jwst_asdf(filename, None)
    # Process FITS files (including ASDF-in-FITS)
    else:
        with fits.open(filename) as hdulist:
            coords = coordinates_from_header(hdulist['SCI'].header)

            if ASDF_EXTENSION_NAME in hdulist:
                # See above: eventually we will get GWCS data from ASDF itself
                # but for now we're faking it and using the WCS data from FITS
                data = _load_jwst_asdf(hdulist, coords)
            else:
                data = _load_jwst_fits(hdulist, coords)

    return data
