from __future__ import print_function

from os.path import basename
from collections import defaultdict

from glue.core import Data
from glue.core.coordinates import coordinates_from_header
from glue.config import data_factory
from glue.core.data_factories import has_extension
from glue.external.astro import fits


@data_factory('Generic FITS', has_extension('fits fit'))
def _load_fits_generic(filename, **kwargs):
    hdulist = fits.open(filename)
    groups = defaultdict(Data)
    for extnum, hdu in enumerate(hdulist):
        if not isinstance(hdu, fits.TableHDU) and\
           hdu.data is not None:
            shape = hdu.data.shape
            if shape not in groups:
                label = '{}[{}]'.format(
                    basename(filename).split('.', 1)[0],
                    'x'.join((str(x) for x in shape))
                )
                data = Data(label=label)
                data.coords = coordinates_from_header(hdu.header)
                groups[shape] = data
            else:
                data = groups[shape]
            data.add_component(component=hdu.data,
                               label=hdu.header.get('EXTNAME', 'EXT[{}]'.format(str(extnum))))
    return [data for data in groups.itervalues()]
