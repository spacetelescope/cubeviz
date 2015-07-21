from __future__ import print_function

import numpy as np

from .core.data_objects import CubeData, SpectrumData

if __name__ == '__main__':
    cube_data = CubeData.read("/Users/nearl/Desktop/cube_tools_demo_data/manga-7443-12703-LOGCUBE.fits",
                            format='fits')
    spec_data = SpectrumData.read(
        "/Users/nearl/Desktop/cube_tools_demo_data/manga-7443-12703-LOGCUBE.fits",
                            format='fits')

    print('disp', cube_data[:, 0, 0].dispersion[0:10])
    print('flux', cube_data[:, 0, 0].get_flux())

    # import matplotlib.pyplot as plt
    #
    # plt.plot(cube_data[:, 50, 50].dispersion,
    #          cube_data[:, 50, 50].flux)
    # plt.show()