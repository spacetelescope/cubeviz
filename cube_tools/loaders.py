from __future__ import print_function

from os.path import basename

from astropy.table import Table

from glue.core import Data, Component
from glue.config import data_factory
from glue.core.data_factories.helpers import has_extension
from glue.core.coordinates import coordinates_from_header, coordinates_from_wcs
from glue.external.astro import fits

from .core.data_objects import CubeData


@data_factory("STcube", has_extension("fits fit"))
def read_cube(filename, **kwargs):
    cube_data = CubeData.read(filename)

    data = Data()
    data.coords = coordinates_from_wcs(cube_data.wcs)
    data.add_component(Component(cube_data), label="cube")

    return data


@data_factory('Generic FITS', has_extension('fits fit'))
def _load_fits_generic(filename, **kwargs):
    hdulist = fits.open(filename)
    groups = dict()
    label_base = basename(filename).rpartition('.')[0]

    if not label_base:
        label_base = basename(filename)

    for extnum, hdu in enumerate(hdulist):
        if hdu.data is not None:
            hdu_name = hdu.name if hdu.name else str(extnum)
            if is_image_hdu(hdu):
                shape = hdu.data.shape
                try:
                    data = groups[shape]
                except KeyError:
                    label = '{}[{}]'.format(
                        label_base,
                        'x'.join(str(x) for x in shape)
                    )
                    data = Data(label=label)
                    data.coords = coordinates_from_header(hdu.header)
                    groups[shape] = data
                data.add_component(component=hdu.data,
                                   label=hdu_name)
            elif is_table_hdu(hdu):
                # Loop through columns and make component list
                table = Table(hdu.data)
                table_name = '{}[{}]'.format(
                    label_base,
                    hdu_name
                )
                for column_name in table.columns:
                    column = table[column_name]
                    shape = column.shape
                    data_label = '{}[{}]'.format(
                        table_name,
                        'x'.join(str(x) for x in shape)
                    )
                    try:
                        data = groups[data_label]
                    except KeyError:
                        data = Data(label=data_label)
                        groups[data_label] = data
                    component = Component(column, units=column.unit)
                    data.add_component(component=component,
                                       label=column_name)
    return [data for data in groups.itervalues()]


# Utilities
def is_image_hdu(hdu):
    from astropy.io.fits.hdu import PrimaryHDU, ImageHDU
    return reduce(lambda x, y: x | isinstance(hdu, y),
                  (PrimaryHDU, ImageHDU), False)


def is_table_hdu(hdu):
    from astropy.io.fits.hdu import TableHDU, BinTableHDU
    return reduce(lambda x, y: x | isinstance(hdu, y),
                  (TableHDU, BinTableHDU), False)
