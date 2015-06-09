from __future__ import print_function

from os.path import basename
from collections import defaultdict

from glue.core import Data, Component
from glue.core.coordinates import coordinates_from_header
from glue.config import data_factory
from glue.core.data_factories import has_extension
from glue.external.astro import fits

import numpy as np
from cube_tools.core import CubeData
import astropy.units as u


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


@data_factory("Cube Data", has_extension("fits fit"))
def read_cube(filename, **kwargs):
    # cdata = CubeData.read(filename)
    cdata = fits.open(filename)
    print(cdata.info())

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