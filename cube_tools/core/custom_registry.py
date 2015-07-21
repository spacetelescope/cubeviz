from __future__ import print_function

from astropy.io import registry
from astropy.io import fits
from astropy.wcs import WCS
from astropy.nddata import StdDevUncertainty
import astropy.units as u
from warnings import warn

from .data_objects import CubeData, SpectrumData, ImageData


def fits_cube_reader(filename):
    hdulist = fits.open(filename)
    header = hdulist[1].header

    try:
        unit = u.Unit(hdulist[1].header['BUNIT'].split(' ')[-1])
    except (KeyError, ValueError):
        warn("Could not find 'BUNIT' in WCS header; assuming"
                "'erg/s/cm^2/Angstrom/voxel'")
        # TODO this is MaNGA-specific
        unit = u.Unit('erg/s/cm^2/Angstrom/voxel')

    return CubeData(data=hdulist[1].data,
                    uncertainty=StdDevUncertainty(hdulist[2].data),
                    mask=hdulist[3].data.astype(int),
                    wcs=WCS(header),
                    unit=unit)


def fits_spectrum_reader(filename):
    hdulist = fits.open(filename)
    header = hdulist[1].header

    try:
        unit = u.Unit(hdulist[1].header['CUNIT'].split(' ')[-1])
    except KeyError:
        warn("Could not find 'CUNIT' in WCS header; assuming 'Jy'")
        unit = u.Unit('Jy')

    return SpectrumData(data=hdulist[1].data[:,25,25],
                        uncertainty=StdDevUncertainty(hdulist[2].data[:,25,
                                                      25]),
                        mask=hdulist[3].data[:,25,25].astype(int),
                        wcs=WCS(header),
                        unit=unit)


def fits_identify(origin, *args, **kwargs):
    return isinstance(args[0], basestring) and \
           args[0].lower().split('.')[-1] in ['fits', 'fit']

try:
    registry.register_reader('fits', CubeData, fits_cube_reader)
    registry.register_reader('fits', SpectrumData, fits_spectrum_reader)
    registry.register_identifier('fits', CubeData, fits_identify)
    registry.register_identifier('fits', SpectrumData, fits_identify)
except Exception:
    warn('Items already exist in IO registry.')
