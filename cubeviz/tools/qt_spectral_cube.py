from __future__ import absolute_import, division, print_function
from spectral_cube import SpectralCube, BooleanArrayMask
from spectral_cube import cube_utils

import numpy as np
import itertools

from astropy import convolution

try:
    from scipy import ndimage
    scipyOK = True
except ImportError:
    scipyOK = False


def dummy_function():
    """Place holder for AbortWindow update function"""
    pass


class QSpectralCube(SpectralCube):

    update_function = dummy_function
    abort = False

    def spatial_smooth_median(self, ksize, **kwargs):
        """
        Smooth the image in each spatial-spatial plane of the cube using a median filter.

        Parameters
        ----------
        ksize : int
            Size of the median filter (scipy.ndimage.filters.median_filter)
        kwargs : dict
            Passed to the convolve function
        """
        if not scipyOK:
            raise ImportError("Scipy could not be imported: this function won't work.")

        shape = self.shape

        # "imagelist" is a generator
        # the boolean check will skip smoothing for bad spectra
        # TODO: should spatial good/bad be cached?
        imagelist = ((self.filled_data[ii],
                      self.mask.include(view=(ii, slice(None), slice(None))))
                      for ii in range(self.shape[0]))

        def _gsmooth_image(args):
            """
            Helper function to smooth a spectrum
            """
            (im, includemask),kwargs = args
            if self.abort:
                return
            else:
                self.update_function()
            if includemask.any():
                return ndimage.filters.median_filter(im, size=ksize)
            else:
                return im

        # could be numcores, except _gsmooth_spectrum is unpicklable
        with cube_utils._map_context(1) as map:
            smoothcube_ = np.array([x for x in
                                    map(_gsmooth_image, zip(imagelist,
                                                            itertools.cycle([kwargs]),
                                                           )
                                       )
                                  ])
        if self.abort:
            return
        # TODO: do something about the mask?
        newcube = self._new_cube_with(data=smoothcube_, wcs=self.wcs,
                                      mask=self.mask, meta=self.meta,
                                      fill_value=self.fill_value)

        return newcube

    def spatial_smooth(self, kernel,
                       #numcores=None,
                       convolve=convolution.convolve, **kwargs):
        """
        Smooth the image in each spatial-spatial plane of the cube.

        Parameters
        ----------
        kernel : `~astropy.convolution.Kernel2D`
            A 2D kernel from astropy
        convolve : function
            The astropy convolution function to use, either
            `astropy.convolution.convolve` or
            `astropy.convolution.convolve_fft`
        kwargs : dict
            Passed to the convolve function
        """

        shape = self.shape

        # "imagelist" is a generator
        # the boolean check will skip smoothing for bad spectra
        # TODO: should spatial good/bad be cached?
        imagelist = ((self.filled_data[ii],
                     self.mask.include(view=(ii, slice(None), slice(None))))
                     for ii in range(self.shape[0]))

        def _gsmooth_image(args):
            """
            Helper function to smooth an image
            """
            (im, includemask),kernel,kwargs = args
            if self.abort:
                return
            else:
                self.update_function()
            if includemask.any():
                return convolve(im, kernel, normalize_kernel=True, **kwargs)
            else:
                return im

        # could be numcores, except _gsmooth_spectrum is unpicklable
        with cube_utils._map_context(1) as map:
            smoothcube_ = np.array([x for x in
                                    map(_gsmooth_image, zip(imagelist,
                                                            itertools.cycle([kernel]),
                                                            itertools.cycle([kwargs]),
                                                           )
                                       )
                                  ])
        if self.abort:
            return

        # TODO: do something about the mask?
        newcube = self._new_cube_with(data=smoothcube_, wcs=self.wcs,
                                      mask=self.mask, meta=self.meta,
                                      fill_value=self.fill_value)

        return newcube

    def spectral_smooth_median(self, ksize, **kwargs):
        """
        Smooth the cube along the spectral dimension

        Parameters
        ----------
        ksize : int
            Size of the median filter (scipy.ndimage.filters.median_filter)
        kwargs : dict
            Passed to the convolve function
        """

        if not scipyOK:
            raise ImportError("Scipy could not be imported: this function won't work.")

        shape = self.shape

        # "cubelist" is a generator
        # the boolean check will skip smoothing for bad spectra
        # TODO: should spatial good/bad be cached?
        cubelist = ((self.filled_data[:,jj,ii],
                     self.mask.include(view=(slice(None), jj, ii)))
                    for jj in range(self.shape[1])
                    for ii in range(self.shape[2]))

        def _gsmooth_spectrum(args):
            """
            Helper function to smooth a spectrum
            """
            (spec, includemask),kwargs = args
            if self.abort:
                return
            else:
                self.update_function()
            if any(includemask):
                return ndimage.filters.median_filter(spec, size=ksize)
            else:
                return spec

        # could be numcores, except _gsmooth_spectrum is unpicklable
        with cube_utils._map_context(1) as map:
            smoothcube_ = np.array([x for x in
                                    map(_gsmooth_spectrum, zip(cubelist,
                                                               itertools.cycle([kwargs]),
                                                              )
                                       )
                                   ]
                                  )
        if self.abort:
            return

        # empirical: need to swapaxes to get shape right
        # cube = np.arange(6*5*4).reshape([4,5,6]).swapaxes(0,2)
        # cubelist.T.reshape(cube.shape) == cube
        smoothcube = smoothcube_.T.reshape(shape)

        # TODO: do something about the mask?
        newcube = self._new_cube_with(data=smoothcube, wcs=self.wcs,
                                      mask=self.mask, meta=self.meta,
                                      fill_value=self.fill_value)

        return newcube

    def spectral_smooth(self, kernel,
                        #numcores=None,
                        convolve=convolution.convolve,
                        **kwargs):
        """
        Smooth the cube along the spectral dimension

        Parameters
        ----------
        kernel : `~astropy.convolution.Kernel1D`
            A 1D kernel from astropy
        convolve : function
            The astropy convolution function to use, either
            `astropy.convolution.convolve` or
            `astropy.convolution.convolve_fft`
        kwargs : dict
            Passed to the convolve function
        """

        shape = self.shape

        # "cubelist" is a generator
        # the boolean check will skip smoothing for bad spectra
        # TODO: should spatial good/bad be cached?
        cubelist = ((self.filled_data[:,jj,ii],
                     self.mask.include(view=(slice(None), jj, ii)))
                    for jj in range(self.shape[1])
                    for ii in range(self.shape[2]))

        def _gsmooth_spectrum(args):
            """
            Helper function to smooth a spectrum
            """
            (spec, includemask),kernel,kwargs = args
            if self.abort:
                return
            else:
                self.update_function()
            if any(includemask):
                return convolve(spec, kernel, normalize_kernel=True, **kwargs)
            else:
                return spec

        # could be numcores, except _gsmooth_spectrum is unpicklable
        with cube_utils._map_context(1) as map:
            smoothcube_ = np.array([x for x in
                                    map(_gsmooth_spectrum, zip(cubelist,
                                                               itertools.cycle([kernel]),
                                                               itertools.cycle([kwargs]),
                                                              )
                                       )
                                   ]
                                  )
        if self.abort:
            return
        # empirical: need to swapaxes to get shape right
        # cube = np.arange(6*5*4).reshape([4,5,6]).swapaxes(0,2)
        # cubelist.T.reshape(cube.shape) == cube
        smoothcube = smoothcube_.T.reshape(shape)

        # TODO: do something about the mask?
        newcube = self._new_cube_with(data=smoothcube, wcs=self.wcs,
                                      mask=self.mask, meta=self.meta,
                                      fill_value=self.fill_value)

        return newcube

    def abort_function(self):
        self.abort = True
