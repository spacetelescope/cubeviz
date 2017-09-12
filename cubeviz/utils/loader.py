# Licensed under a 3-clause BSD style license - see LICENSE.rst

from glue.config import data_factory
from glue.core import Data
import asdf


def is_jwst_data_cube(filename, **kwargs):
    return filename.endswith('.asdf')

def is_generic_data_cube(filename, **kwargs):
    pass


@data_factory('JWST data cube loader', is_jwst_data_cube, priority=1100)
def read_jwst_data_cube(filename):
    asdffile = asdf.open(filename)
    return Data(data=asdffile.tree['data'])

@data_factory('Generic data cube loader', is_generic_data_cube, priority=1099)
def read_generic_data_cube(filename):
    pass
