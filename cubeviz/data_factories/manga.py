# Licensed under a 3-clause BSD style license - see LICENSE.rst
from os.path import basename, splitext

from glue.config import data_factory
from glue.core import Data
from glue.core.coordinates import coordinates_from_header

from astropy.io import fits

import numpy as np

from ..listener import CUBEVIZ_LAYOUT
from ..layout import FLUX, ERROR, MASK


def is_manga_data_cube(filename, **kwargs):
    hdulist = fits.open(filename)

    primary = hdulist['PRIMARY'].header

    if not primary.get('TELESCOP', '').startswith('SDSS 2.5-M'):
        return False

    if not primary.get('INSTRUME', '').startswith('MaNGA'):
        return False

    return True

#@data_factory('MaNGA data cube loader', is_manga_data_cube, priority=1200)
def read_manga_data_cube(filename):
    hdulist = fits.open(filename)

    flux = hdulist['FLUX']
    var = hdulist['IVAR']
    mask = hdulist['MASK']

    label = "MaNGA data cube: {}".format(splitext(basename(filename))[0])
    data = Data(label=label)

    data.coords = coordinates_from_header(flux.header)
    data.meta[CUBEVIZ_LAYOUT] = 'MANGA'

    data.add_component(component=flux.data, label=FLUX)
    data.add_component(component=var.data, label=ERROR)
    data.add_component(component=mask.data, label=MASK)

    return data
