from __future__ import print_function

from os.path import basename
from collections import defaultdict

from glue.core import Data, Component
from glue.core.coordinates import coordinates_from_header
from glue.config import data_factory
from glue.core.data_factories.helpers import has_extension
from glue.external.astro import fits

import numpy as np
import astropy.units as u
from astropy.table import Table


@data_factory('Generic FITS', has_extension('fits fit'))
def _load_fits_generic(filename, **kwargs):
    hdulist = fits.open(filename)
    groups = dict()
    label_base =  basename(filename).rpartition('.')[0]
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
                    component = Component.autotyped(column, units=column.unit)
                    data.add_component(component=component,
                                       label=column_name)
    return [data for data in groups.itervalues()]


@data_factory("Cube Data", has_extension("fits fit"))
def read_cube(filename, **kwargs):
    # cdata = CubeData.read(filename)
    cdata = fits.open(filename)

    flux = cdata['FLUX'].data

    try:
        flux_unit = u.Quantity(cdata['FLUX'].header['BUNIT']).unit
    except:
        flux_unit = u.Unit('erg/s/cm^2/Angstrom/voxel')

    disp = np.empty(shape=flux.shape)
    disp[:, 0, 0] = cdata['WAVE'].data
    disp_unit = u.Unit(cdata['FLUX'].header['CUNIT3'])
    uncert = cdata['IVAR'].data
    mask = cdata['MASK'].data

    data = Data()
    data.add_component(component=Component(data=flux,
                                           units=flux_unit.to_string()),
                                           label="flux")
    data.add_component(component=Component(data=disp,
                                           units=disp_unit.to_string()),
                                           label="disp")
    data.add_component(component=Component(data=uncert,
                                           units=flux_unit.to_string()),
                                           label="uncertainty")
    # data.add_component(component=Component(data=cdata))

    header_info = np.empty(shape=flux.shape)

    try:
        header_info[0] = cdata.wcs.wcs['CRVAL3']
        header_info[1] = cdata.wcs.wcs['CD3_3']
        header_info[2] = cdata.wcs.wcs['CRPIX3']
    except:
        pass

    data.add_component(component=header_info,  # np.resize(cdata.header, cdata.data.shape),
                       label="header")
    data.add_component(component=mask,
                       label="mask")
    return data


# Utilities
def is_image_hdu(hdu):
    from astropy.io.fits.hdu import PrimaryHDU, ImageHDU
    return reduce(lambda x, y: x | isinstance(hdu, y), (PrimaryHDU, ImageHDU), False)


def is_table_hdu(hdu):
    from astropy.io.fits.hdu import TableHDU, BinTableHDU
    return reduce(lambda x, y: x | isinstance(hdu, y), (TableHDU, BinTableHDU), False)
