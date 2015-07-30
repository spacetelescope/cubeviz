import numbers
import numpy as np
from astropy.nddata import (NDData, NDSlicingMixin, NDArithmeticMixin)
import astropy.units as u
from astropy.io import fits


class CubeDataError(Exception):
    """General error related to CubeData"""


class BaseData(NDData, NDArithmeticMixin):
    """
    Base class for all CubeData objects and their slices.
    """
    def __init__(self, *args, **kwargs):
        super(BaseData, self).__init__(*args, **kwargs)

    @property
    def shape(self):
        return self.data.shape

    @classmethod
    def read(cls, *args, **kwargs):
        """
        Weirdly, this must have a docstring or astropy crashes.
        """
        from . import custom_registry
        return custom_registry.registry.read(cls, *args, **kwargs)

    def __len__(self):
        return self.data.size

    # TODO: self.data cannot be set directly in NDData objects; a round
    # about way for arithmetic to work on the data itself is to create NDData
    # objects. This seems hackneyed: should investigate.
    def __add__(self, other):
        if not issubclass(type(other), NDData):
            if isinstance(other, numbers.Number):
                new = np.empty(shape=self.data.shape)
                new.fill(other)
                other = new

            other = NDData(other, wcs=self.wcs, unit=self.unit)
            return self.add(other)

        other = NDData(other.data, wcs=self.wcs, unit=other.unit,
                       uncertainty=other.uncertainty, mask=other.mask)

        return self.add(other)

    def __sub__(self, other):
        if not issubclass(type(other), NDData):
            if isinstance(other, numbers.Number):
                new = np.empty(shape=self.data.shape)
                new.fill(other)
                other = new

            other = NDData(other, wcs=self.wcs, unit=self.unit)
            return self.subtract(other)

        other = NDData(other.data, wcs=self.wcs, unit=other.unit,
                       uncertainty=other.uncertainty, mask=other.mask)

        return self.subtract(other)

    def __mul__(self, other):
        if not issubclass(type(other), NDData):
            if isinstance(other, numbers.Number):
                new = np.empty(shape=self.data.shape)
                new.fill(other)
                other = new

            other = NDData(other, wcs=self.wcs, unit=self.unit)
            return self.multiply(other)

        other = NDData(other.data, wcs=self.wcs, unit=other.unit,
                       uncertainty=other.uncertainty, mask=other.mask)

        return self.multiply(other)

    def __div__(self, other):
        if not issubclass(type(other), NDData):
            if isinstance(other, numbers.Number):
                new = np.empty(shape=self.data.shape)
                new.fill(other)
                other = new

            other = NDData(other, wcs=self.wcs, unit=self.unit)
            return self.divide(other)

        other = NDData(other.data, wcs=self.wcs, unit=other.unit,
                       uncertainty=other.uncertainty, mask=other.mask)

        return self.divide(other)

    def export_fits(self, path='out.fits'):
        data_hdu = fits.ImageHDU(self.data, name='data')
        ivar_hdu = fits.ImageHDU(self.uncertainty.array, name='ivar')
        mask_hdu = fits.ImageHDU(self.mask.astype(int), name='mask')

        prihead = self.wcs.to_header()
        prihdu = fits.PrimaryHDU(header=prihead)

        thdulist = fits.HDUList([prihdu, data_hdu, ivar_hdu, mask_hdu])
        thdulist.writeto('{}.fits'.format(path))


class CubeData(BaseData):
    """
    Container object for IFU cube data.
    """

    def __init__(self, *args, **kwargs):
        super(CubeData, self).__init__(*args, **kwargs)

    def __getitem__(self, item):
        return self.data[item]

    def get_spectrum(self, x, y):
        new_data = self.data[:, y, x]

        if self.uncertainty is not None:
            new_uncertainty = self.uncertainty[:, x, y]
        else:
            new_uncertainty = None

        if self.mask is not None:
            new_mask = self.mask[:, x, y]
        else:
            new_mask = None

        return SpectrumData(new_data, uncertainty=new_uncertainty,
                            mask=new_mask, wcs=self.wcs,
                            meta=self.meta, unit=self.unit)

    def collapse_to_spectrum(self, method='mean', filter_mask=None):
        mdata = np.ma.masked_array(self.data, mask=~filter_mask)
        udata = np.ma.masked_array(self.uncertainty.array, mask=~filter_mask)

        if method == 'mean':
            new_mdata = mdata.mean(axis=1).mean(axis=1)
            new_udata = udata.mean(axis=1).mean(axis=1)
        elif method == 'median':
            new_mdata = mdata.median(axis=1).median(axis=1)
            new_udata = udata.median(axis=1).median(axis=1)

        return SpectrumData(new_mdata.data,
                            uncertainty=self.uncertainty.__class__(
                                new_udata.data),
                            mask=udata.mask, wcs=self.wcs, meta=self.meta,
                            unit=self.unit), ~new_mdata.mask

    def collapse_to_image(self, wavelength_range=None, method="mean", axis=0):
        mdata = np.ma.masked_array(self.data, mask=self.mask)

        # TODO: extend this to be *actual* wavelengths
        if wavelength_range is not None:
            mdata = mdata[slice(*wavelength_range), :, :]

        if method == "mean":
            new_data = mdata.mean(axis=axis)
        elif method == "median":
            new_data = np.ma.median(mdata, axis=axis)
        elif method == "mode":
            # TODO: requires a more elegant solution; scipy's mode is too
            # slow and doesn't really make sense for a bunch of floats
            pass
        else:
            raise NotImplementedError("No such method {}".format(method))

        return ImageData(new_data.data, uncertainty=None, mask=self.mask,
                         wcs=self.wcs, meta=self.meta, unit=self.unit)


class SpectrumData(BaseData):
    """
    Container object for spectra data included within the Cube data object.
    """
    def __init__(self, *args, **kwargs):
        super(SpectrumData, self).__init__(*args, **kwargs)

        disp_data = np.arange(self.wcs.wcs.crpix[2],
                              self.wcs.wcs.crpix[2] + self.data.shape[0])
        disp_unit = u.Unit(self.wcs.wcs.cunit[2])

        if self.wcs.wcs.ctype[2] == 'WAVE-LOG':
            disp_data = self.wcs.wcs.crval[2] * \
                        np.exp(self.wcs.wcs.cd[2][2] * (disp_data -
                                                    self.wcs.wcs.crpix[2])
                               / self.wcs.wcs.crval[2])

        # disp_data = np.linspace(disp_data[0], disp_data[-1], self.data.size)
        self._dispersion = u.Quantity(disp_data, disp_unit, copy=False)
        self._flux = u.Quantity(self.data, self.unit, copy=False)
        self._error = u.Quantity(self.uncertainty.array, self.unit) if \
            self.uncertainty is not None else None

    def __getitem__(self, item):
        print(item)
        return u.Quantity(self.data[item], self.unit, copy=False)

    @property
    def shape(self):
        return self.data.shape

    @property
    def flux(self):
        return self._flux

    @property
    def dispersion(self):
        return self._dispersion

    @property
    def error(self):
        return self._error

    def get_flux(self, convert_unit=None):
        if convert_unit is None:
            return self._flux

        return self._flux.to(convert_unit)

    def get_error(self, convert_unit=None):
        if convert_unit is None:
            return self._error

        return self._error.to(convert_unit)

    def get_dispersion(self, convert_unit=None):
        if convert_unit is None:
            return self._dispersion

        return self._dispersion.to(convert_unit)


class ImageData(BaseData):
    """
    Container object for image data included within the Cube data object.
    """
    def __init__(self, *args, **kwargs):
        super(ImageData, self).__init__(*args, **kwargs)

    def __getitem__(self, item):
        return u.Quantity(self.data[item], self.unit, copy=False)

    def ravel(self):
        return self.data.ravel()
