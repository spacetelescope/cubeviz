from astropy.io import registry
from data_objects import CubeData
from astropy.wcs import WCS
from astropy.nddata import StdDevUncertainty
import astropy.units as u
import numpy as np


def fits_cube_reader(filename):
    from astropy.io import fits
    hdulist = fits.open(filename)
    header = hdulist[1].header

    try:
        unit = u.Unit(hdulist[1].header['BUNIT'].split(' ')[-1])
    except:
        # TODO this is MaNGA-specific
        unit = u.Unit('erg/s/cm^2/Angstrom/voxel')

    # TODO: read in proper units from header.
    return CubeData(data=hdulist[1].data,
                    #header=np.array(hdulist[0].header.__repr__().split('\n')),
                    uncertainty=StdDevUncertainty(hdulist[3].data),
                    mask=hdulist[2].data.astype(int),
                    wcs=None, #WCS(hdulist[1].header),
                    unit=unit)


def fits_identify(origin, *args, **kwargs):
    return isinstance(args[0], basestring) and \
           args[0].lower().split('.')[-1] in ['fits', 'fit']


registry.register_reader('fits', CubeData, fits_cube_reader)
registry.register_identifier('fits', CubeData, fits_identify)