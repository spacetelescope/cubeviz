# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import numpy as np
import matplotlib.pyplot as plt
from astropy import log
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from photutils import SkyRectangularAperture
from .extern.utils import Cutout2D


def make_cutouts(table, data, wcs, image_label, clobber=False):
    """
    Make cutouts from a 2D image and write them to FITS files.

    Parameters
    ----------
    table : `~astropy.table.QTable`
        An astropy quantity table defining the sources to cut out.
        Table must have the following columns:
            'id', 'ra', 'dec', 'cutout_x_size', 'cutout_y_size'
        'cutout_x_size' and 'cutout_y_size' should be
        `~astropy.units.Quantity` objects.

    data : `~numpy.ndarray`

    wcs : `~astropy.wcs.WCS`

    image_label : str

    clobber : bool, optional
    """

    for obj in table:
        position = SkyCoord(obj['ra'], obj['dec'])
        y_pix = obj['cutout_y_size'] / obj['spatial_pixel_scale']
        x_pix = obj['cutout_x_size'] / obj['spatial_pixel_scale']
        cutout_size = (y_pix, x_pix)
        cutout = Cutout2D(data, position, size=cutout_size, wcs=wcs,
                          mode='partial')
        path = '{0}_cutouts'.format(image_label)
        fname = '{0}_{1}_cutout.fits'.format(obj['id'], image_label)
        fname = os.path.join(path, fname)
        if not os.path.exists(path):
            os.mkdir(path)
        fits.writeto(fname, cutout.data, cutout.wcs.to_header(),
                     clobber=clobber)
        log.info('Wrote: ' + fname)


def show_cutout_with_slit(table, obj_id, image_label, **kwargs):
    """
    Show cutout images with the slit superimposed.

    Parameters
    ----------
    table : `~astropy.table.QTable`
        An astropy quantity table defining the sources to cut out.
        Table must have the following columns:
            'id', 'ra', 'dec', 'cutout_x_size', 'cutout_y_size'
        'cutout_x_size' and 'cutout_y_size' should be
        `~astropy.units.Quantity` objects.

    obj_id : str

    image_label : str

    **kwargs :
        Any additional keyword arguments will be passed to the aperture
        plotting function.
    """

    path = '{0}_cutouts'.format(image_label)
    cutout_fname = '{0}_{1}_cutout.fits'.format(obj_id, image_label)
    cutout_fname = os.path.join(path, cutout_fname)
    with fits.open(cutout_fname) as fo:
        data = fo[0].data
        wcs = WCS(fo[0].header)
    idx = np.where(table['id'] == obj_id)
    obj = table[idx]
    position = SkyCoord(obj['ra'], obj['dec'])
    aper = SkyRectangularAperture(position, obj['slit_width'],
                                  obj['slit_length'], theta=90.*u.deg)
    aper_pix = aper.to_pixel(wcs)
    plt.imshow(data, cmap='Greys_r')
    aper_pix.plot(**kwargs)
