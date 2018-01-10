# Licensed under a 3-clause BSD style license - see LICENSE.rst
from os.path import basename, splitext

from glue.config import data_factory
from glue.core import Data
from glue.core.coordinates import coordinates_from_header

from astropy.io import fits

import numpy as np

from ..listener import CUBEVIZ_LAYOUT
from ..layout import FLUX, ERROR, MASK


def is_kmos_data_cube(filename, **kwargs):
    hdulist = fits.open(filename)

    primary = hdulist['PRIMARY'].header

    if not primary.get('TELESCOP', '').startswith('ESO-VLT-U1'):
        return False

    if not primary.get('INSTRUME', '').startswith('KMOS'):
        return False

    if not primary.get('HIERARCH ESO PRO TECH').startswith('IFU'):
        return False

    return True

#@data_factory('KMOS data cube loader', is_kmos_data_cube, priority=1200)
def read_kmos_data_cube(filename):
    hdulist = fits.open(filename)

    primary, sci, noise = hdulist[0:3]

    label = "KMOS data cube: {}".format(splitext(basename(filename))[0])
    data = Data(label=label)

    data.coords = coordinates_from_header(sci.header)
    data.meta[CUBEVIZ_LAYOUT] = 'KMOS'

    data.add_component(component=sci.data, label=FLUX)
    data.add_component(component=noise.data, label=ERROR)
    data.add_component(component=np.empty(sci.data.shape), label=MASK)

    return data
