from __future__ import print_function

import os.path
from collections import defaultdict, namedtuple

import numpy as np
from astropy.io import registry
from astropy.io import fits
from astropy.wcs import WCS
from astropy.nddata import StdDevUncertainty
import astropy.units as u
from warnings import warn

from .data_objects import CubeData, SpectrumData, ImageData, CubeDataError
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


def fits_spectrum_reader(filename, hdu=1, is_record=False, normalize=False,
                         **kwargs):
    hdulist = fits.open(filename, **kwargs)
    header = hdulist[hdu].header

    try:
        unit = u.Unit(hdulist[hdu].header['BUNIT'].strip())
    except (KeyError, ValueError):
        warn("Could not find 'BUNIT' in WCS header, or the value "
             "could be parsed by as an astropy unit. Assuming 'Jy'")
        unit = u.Unit('Jy')

    data = hdulist[hdu].data['DATA'] if is_record else hdulist[hdu].data

    try:
        if is_record:
            unc_data = hdulist[hdu].data['VAR']
        else:
            unc_data = hdulist[hdu+2].data

        unc = StdDevUncertainty(unc_data/unc_data.max() if normalize else
                                unc_data)
    except:
        unc = None

    try:
        mask = hdulist[hdu].data['QUALITY'] if is_record else hdulist[
            hdu+1].data
        mask = mask.astype(int)
    except:
        mask = None

    return SpectrumData(data=data/data.max() if normalize else data,
                        uncertainty=unc,
                        mask=mask,
                        wcs=WCS(header),
                        unit=unit)


def table_spectrum_reader(filename, **kwargs):
    x, y, err = np.loadtxt(filename, unpack=True)

    unit = u.Unit('erg s-1 cm-2 A-1')
    spec_data = SpectrumData(data=y, wcs=WCS(), unit=unit)
    spec_data.dispersion = u.Quantity(x, u.Unit('micrometer'))

    return spec_data


def fits_image_reader(filename, hdu=0, is_record=False, **kwargs):
    hdulist = fits.open(filename, **kwargs)
    header = hdulist[hdu].header

    try:
        unit = u.Unit(hdulist[hdu].header['CUNIT1'].split(' ')[-1])
    except KeyError:
        warn("Could not find 'CUNIT' in WCS header; assuming 'Jy'")
        unit = u.Unit('Jy')

    data = hdulist[hdu].data['FLUX'][0] if is_record else hdulist[hdu].data
    try:
        unc = StdDevUncertainty(hdulist[hdu].data['IVAR'][0] if is_record else
                                hdulist[hdu+1].data)
    except:
        unc = None

    try:
        mask = hdulist[hdu].data['MASK'][0] if is_record else hdulist[hdu+2].data
    except:
        mask = None

    return ImageData(data=data, wcs=WCS(header), unit=unit, mask=mask,
                     uncertainty=unc)


def fits_identify(origin, *args, **kwargs):
    if args[0] is None and isinstance(args[2], fits.hdu.hdulist.HDUList):
        return True
    try:
        result = has_extension('fits fit')(args[0])
    except Exception:
        result = False
    return result


def table_spectrum_identify(origin, *args, **kwargs):
    return isinstance(args[0], basestring) and \
           args[0].lower().split('.')[-1] in ['dat']

try:
    registry.register_reader('fits', CubeData, fits_cube_reader)
    registry.register_reader('fits', SpectrumData, fits_spectrum_reader)
    registry.register_reader('fits', ImageData, fits_image_reader)
    registry.register_reader('dat', SpectrumData, table_spectrum_reader)
    registry.register_identifier('fits', CubeData, fits_identify)
    registry.register_identifier('fits', SpectrumData, fits_identify)
    registry.register_identifier('fits', ImageData, fits_identify)
    registry.register_identifier('dat', SpectrumData, table_spectrum_identify)
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
