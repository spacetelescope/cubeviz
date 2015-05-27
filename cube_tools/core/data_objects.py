import numpy as np
from astropy.nddata import (NDData, NDSlicingMixin, NDArithmeticMixin)
from astropy.wcs import WCS
from astropy.units import Unit
from specutils import Spectrum1D


class CubeData(NDData, NDArithmeticMixin):
    """
    Container object for IFU cube data.
    """

    def __init__(self, *args, **kwargs):
        super(CubeData, self).__init__(*args, **kwargs)

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
            new_wcs = self.wcs[item]
        else:
            new_wcs = None

        if not isinstance(item[2], slice):
            return ImageData(new_data, uncertainty=new_uncertainty,
                             mask=new_mask, wcs=new_wcs,
                             meta=self.meta, unit=self.unit)
        elif not isinstance(item[0], slice) or not isinstance(item[1], slice):
            return SpectrumData(new_data, new_wcs, unit=self.unit,
                                uncertainty=new_uncertainty, mask=new_mask,
                                meta=self.meta, indexer=None)
        else:
            return self.__class__(new_data, uncertainty=new_uncertainty,
                                  mask=new_mask, wcs=new_wcs,
                                  meta=self.meta, unit=self.unit)

    def __add__(self, other):
        return self.add(other, propagate_uncertainties=True)

    def __sub__(self, other):
        return self.subtract(other, propagate_uncertainties=True)

    def __mul__(self, other):
        return self.multiply(other, propagate_uncertainties=True)

    def __div__(self, other):
        return self.divide(other, propagate_uncertainties=True)


class SpectrumData(Spectrum1D, NDSlicingMixin, NDArithmeticMixin):
    """
    Inheritance wrapper to include the NDData mixins with the Spectrum1D object.
    """

    def __init__(self, *args, **kwargs):
        super(SpectrumData, self).__init__(*args, **kwargs)

    def __add__(self, other):
        return self.add(other, propagate_uncertainties=True)

    def __sub__(self, other):
        return self.subtract(other, propagate_uncertainties=True)

    def __mul__(self, other):
        return self.multiply(other, propagate_uncertainties=True)

    def __div__(self, other):
        return self.divide(other, propagate_uncertainties=True)


class ImageData(NDData, NDSlicingMixin, NDArithmeticMixin):
    """
    Container object for image data included within the Cube data object.
    """

    def __init__(self, *args, **kwargs):
        super(ImageData, self).__init__(*args, **kwargs)

    def __add__(self, other):
        return self.add(other, propagate_uncertainties=True)

    def __sub__(self, other):
        return self.subtract(other, propagate_uncertainties=True)

    def __mul__(self, other):
        return self.multiply(other, propagate_uncertainties=True)

    def __div__(self, other):
        return self.divide(other, propagate_uncertainties=True)


if __name__ == "__main__":
    cube_data1 = CubeData(np.random.sample(size=(3, 3, 3)))
    cube_data2 = CubeData(np.random.sample(size=(3, 3, 3)))

    print(type(cube_data1[:, 0, 0]))
    print(cube_data2)
    print(cube_data1 + cube_data2)
