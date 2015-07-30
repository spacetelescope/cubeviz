from __future__ import print_function

import os.path
from collections import defaultdict, namedtuple

from astropy.io import registry
from astropy.io import fits
from astropy.wcs import WCS
from astropy.nddata import StdDevUncertainty
import astropy.units as u
from warnings import warn

from .data_objects import CubeData, SpectrumData, CubeDataError
from .fits_registry import fits_registry


class CubeDataIOError(CubeDataError):
    """Errors trying to create CubeData using IO methods"""


default_value = {
    'flux': lambda hdu: hdu.data,
    'error': lambda hdu: StdDevUncertainty(hdu.data),
    'mask': lambda hdu: hdu.data.astype(int),
}
Value = namedtuple('Value', 'ext value')


def fits_cube_reader(source, config=None):
    if not isinstance(source, fits.hdu.hdulist.HDUList):
        hdulist = fits.open(source)
    else:
        hdulist = source

    data = None
    if config:
        data = cube_from_config(hdulist, fits_registry[config])
    else:
        for config in reversed(fits_registry):
            try:
                data = cube_from_config(hdulist, fits_registry[config])
                break
            except Exception:
                continue
    if not data:
        raise CubeDataIOError('Cannot find cube in fits file.')

    return data


def cube_from_config(hdulist, config):
    values = defaultdict(lambda: Value(None, None))
    wcs = None

    for ext_type in config:
        params = config[ext_type]
        try:
            ext = params['ext']
            if 'ext_card' in params:
                ext = hdulist[ext].header[params['ext_card']]

            try:
                values[ext_type] = Value(ext,
                                         params['value'](hdulist[ext]))
            except KeyError:
                values[ext_type] = Value(ext,
                                         default_value[ext_type](hdulist[ext]))

            if params.get('wcs'):
                try:
                    wcs = WCS(hdulist[ext].header)
                except Exception:
                    pass
        except (KeyError, IndexError):
            if params.get('required'):
                raise CubeDataIOError(
                    'Required extension "{}" not found.'.format(ext_type)
                )

    try:
        unit = u.Unit(hdulist[values['flux'].ext].header['BUNIT'].split(' ')[-1])
    except (KeyError, ValueError):
        warn("Could not find 'BUNIT' in WCS header; assuming"
             "'erg/s/cm^2/Angstrom/voxel'")
        # TODO this is MaNGA-specific
        unit = u.Unit('erg/s/cm^2/Angstrom/voxel')

    data = CubeData(data=values['flux'].value,
                    uncertainty=values['error'].value,
                    mask=values['mask'].value,
                    wcs=wcs,
                    unit=unit)
    data.meta['hdu_ids'] = [values[ext_type].ext
                            for ext_type in values
                            if values[ext_type].ext is not None]
    return data


def fits_spectrum_reader(filename):
    hdulist = fits.open(filename)
    header = hdulist[1].header

    try:
        unit = u.Unit(hdulist[1].header['CUNIT'].split(' ')[-1])
    except KeyError:
        warn("Could not find 'CUNIT' in WCS header; assuming 'Jy'")
        unit = u.Unit('Jy')

    return SpectrumData(data=hdulist[1].data[:, 25, 25],
                        uncertainty=StdDevUncertainty(
                            hdulist[2].data[:, 25, 25]
                        ),
                        mask=hdulist[3].data[:, 25, 25].astype(int),
                        wcs=WCS(header),
                        unit=unit)


def fits_identify(origin, *args, **kwargs):
    if args[0] is None and isinstance(args[2], fits.hdu.hdulist.HDUList):
        return True
    try:
        result = has_extension('fits fit')(args[0])
    except Exception:
        result = False
    return result

try:
    registry.register_reader('fits', CubeData, fits_cube_reader)
    registry.register_reader('fits', SpectrumData, fits_spectrum_reader)
    registry.register_identifier('fits', CubeData, fits_identify)
    registry.register_identifier('fits', SpectrumData, fits_identify)
except Exception:
    warn('Items already exist in IO registry.')


# Utilities
def _extension(path):
    # extract the extension type from a path
    #  test.fits -> fits
    #  test.gz -> fits.gz (special case)
    #  a.b.c.fits -> fits
    _, path = os.path.split(path)
    if '.' not in path:
        return ''
    stems = path.split('.')[1:]

    # special case: test.fits.gz -> fits.gz
    if len(stems) > 1 and any(x == stems[-1]
                              for x in ['gz', 'gzip', 'bz', 'bz2']):
        return stems[-2]
    return stems[-1]


def has_extension(exts):
    """
    A simple default filetype identifier function

    It returns a function that tests whether its input
    filename contains a particular extension

    Inputs
    ------
    exts : str
      A space-delimited string listing the extensions
      (e.g., 'txt', or 'txt csv fits')

    Returns
    -------
    A function suitable as a factory identifier function
    """

    def tester(x, **kwargs):
        return _extension(x) in set(exts.split())
    return tester
