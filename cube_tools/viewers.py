from __future__ import print_function

from glue import custom_viewer
from glue.clients.ds9norm import DS9Normalize

import numpy as np

# define the galfa-hi viewer
median_rgb_viewer = custom_viewer('MEDIAN RGB Viewer',  # name of viewer
                   data = 'att',
                   red_center = (3621, 10353, 9920),        # center of redwave in pixels
                   blue_center = (3621, 10353, 3880),       # center of bluewave in pixels
                   green_center = (3621, 10353, 6830),      # center of greenwave in pixels
                   red_width =(1, 20, 5),               # width of R channel in pixels
                   blue_width =(1, 20, 5),              # width of G channel in pixels
                   green_width =(1, 20, 5),             # width of B channel in pixels
                   redraw_on_settings_change = True   # rerender data if settings change
                  )


@median_rgb_viewer.plot_data
def draw(axes, data, red_center, blue_center, green_center, red_width, blue_width, green_width, layer):
    """
    Make a 3 color image showing a data slice (g), slice - width (r), slice + width (b)
    data: 3D numpy arrays
    ra, dec, vlsr: 1D array, showing the grid points on each of the axis
    """
    if data is None or data.size == 0 or data.ndim != 3:
        return

    wavelength = 1e10*layer['Wave', :, 0, 0]
    dec = layer['Declination', 0, :, 0]
    ra = layer['Right Ascension', 0, 0, :]

    wave_pix = (wavelength[1] - wavelength[0])

    red_npix_width = int(red_width/wave_pix)
    npix_hw_r    = np.ceil(red_npix_width/2.)
    
    green_npix_width = int(green_width/wave_pix)
    npix_hw_g    = np.ceil(green_npix_width/2.)
    
    blue_npix_width = int(blue_width/wave_pix)
    npix_hw_b    = np.ceil(blue_npix_width/2.)


    # extract rgb sub_datas with some wavelength width
    cenpix_g  = int(np.interp( green_center, wavelength, np.arange(0, len(wavelength))))
    g = data[max(cenpix_g - npix_hw_g, 0):min(cenpix_g + npix_hw_g, data.shape[0]-1), :, :]
    
    cenpix_r  = int(np.interp(red_center, wavelength, np.arange(0, len(wavelength))))
    #cenpix_r  = int((red_center - wavelength.min())/wave_pix)
    r = data[max(cenpix_r - npix_hw_r, 0):min(cenpix_r + npix_hw_r, data.shape[0]-1), :, :]
    
    cenpix_b  = int(np.interp(blue_center, wavelength, np.arange(0, len(wavelength))))
    #cenpix_b = int((blue_center - wavelength.min())/wave_pix)
    b = data[max(cenpix_b - npix_hw_b, 0):min(cenpix_b + npix_hw_b, data.shape[0]-1), :, :]

    # take the mean for each r, g, b slice
    g = np.median(g, axis = 0)
    r = np.median(r, axis = 0)
    b = np.median(b, axis = 0)


    rgb = np.nan_to_num(np.dstack((r, g, b)))

    # manually rescale intensities from 0-1
    norm = DS9Normalize()
    norm.vmin = -0.2
    norm.vmax = 1.
    norm.stretch = 'arcsinh'

    rgb = norm(rgb)
    axes.imshow(rgb, origin='lower', extent = [ra.max(), ra.min(), dec.min(), dec.max()])
    axes.set_xlabel('RA')
    axes.set_ylabel('DEC')
    # axes.set_title(data.label)
