import numpy as np
import numpy.ma as ma
from astropy.nddata import (NDData, NDSlicingMixin, NDArithmeticMixin)
import astropy.units as u
import custom_registry
import numbers


class BaseData(NDData, NDArithmeticMixin, NDSlicingMixin):
    """
    Base class for all CubeData objects and their slices.
    """
    def __init__(self, *args, **kwargs):
        super(BaseData, self).__init__(*args, **kwargs)

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


class CubeData(BaseData):
    """
    Container object for IFU cube data.
    """

    def __init__(self, *args, **kwargs):
        super(CubeData, self).__init__(*args, **kwargs)

        self.spatial_unit = None
        self.spectral_unit = None

    def __getitem__(self, item):
        new_data = self.data[item]

        if self.uncertainty is not None:
            new_uncertainty = self.uncertainty[item]
        else:
            new_uncertainty = None

        if self.mask is not None:
            new_mask = self.mask[item]
        else:
            new_mask = None

        if self.wcs is not None:
            # TODO: this errors with "Cannot downsample a WCS with indexing.
            # Use wcs.sub or wcs.dropaxis if you want to remove axes."
            # need to investigate
            # new_wcs = self.wcs[item]
            new_wcs = self.wcs
        else:
            new_wcs = None

        if not hasattr(item, '__getitem__'):
            return self.__class__(new_data, uncertainty=new_uncertainty,
                                  mask=new_mask, wcs=new_wcs,
                                  meta=self.meta, unit=self.unit)

        if not isinstance(item[0], slice) and (isinstance(item[1], slice) or
                                                   isinstance(item[2], slice)):
            return ImageData(new_data, uncertainty=new_uncertainty,
                             mask=new_mask, wcs=new_wcs,
                             meta=self.meta, unit=self.spatial_unit)
        elif isinstance(item[0], slice) and (not isinstance(item[1], slice)
                                             or not isinstance(item[2], slice)):
            return SpectrumData(new_data, uncertainty=new_uncertainty,
                                mask=new_mask, wcs=new_wcs,
                                meta=self.meta, unit=self.spectral_unit)
        elif all([isinstance(x, slice) for x in item]):
            return self.__class__(new_data, uncertainty=new_uncertainty,
                                  mask=new_mask, wcs=new_wcs,
                                  meta=self.meta, unit=self.unit)
        else:
            return u.Quantity(new_data, self.unit)

    @classmethod
    def read(cls, *args, **kwargs):
        """
        Weirdly, this must have a docstring or astropy crashes.
        """
        return custom_registry.registry.read(cls, *args, **kwargs)

    def collapse(self, wavelength_range=None, method="mean", axis=0):
        mdata = ma.masked_array(self.data, mask=self.mask)

        # TODO: extend this to be *actual* wavelengths
        if wavelength_range is not None:
            mdata = mdata[slice(*wavelength_range), :, :]

        if method == "mean":
            new_data = mdata.mean(axis=axis)
        elif method == "median":
            new_data = np.ma.median(mdata, axis=axis)
        elif method == "mode":
            # TODO: requires a more eligant solution; scipy's mode is too
            # slow and doesn't really make sense for a bunch of floats
            pass
        else:
            raise NotImplementedError("No such method {}".format(method))

        return ImageData(new_data.data, uncertainty=None, mask=mdata.mask,
                         wcs=self.wcs, meta=self.meta, unit=self.unit)


class SpectrumData(BaseData):
    """
    Container object for spectra data included within the Cube data object.
    """

    def __init__(self, *args, **kwargs):
        super(SpectrumData, self).__init__(*args, **kwargs)

        self.convert_flux_unit = None
        self.convert_disp_unit = None

    @property
    def flux(self):
        flux_data = u.Quantity(self.data, self.unit, copy=False)

        if self.convert_flux_unit is None:
            return flux_data

        return flux_data.to(self.convert_flux_unit)

    @property
    def dispersion(self):
        disp_data = u.Quantity(np.arange(self.data.shape[0]), u.Angstrom,
                               copy=False)

        if self.convert_disp_unit is None:
            return disp_data

        return disp_data.to(self.convert_disp_unit)

    def __getitem__(self, item):
        return u.Quantity(self.data[item], self.unit, copy=False)


class ImageData(BaseData):
    """
    Container object for image data included within the Cube data object.
    """

    def __init__(self, *args, **kwargs):
        super(ImageData, self).__init__(*args, **kwargs)

    def __getitem__(self, item):
        return u.Quantity(self.data[item], self.unit, copy=False)
