# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os
import time

import pytest
import numpy as np

from qtpy import QtCore
from glue.core import roi
from cubeviz.tools.smoothing import SelectSmoothing

from ...tests.helpers import (toggle_viewer, select_viewer, left_click,
                      left_button_press, right_button_press, enter_slice_text,
                      assert_all_viewer_indices, assert_slice_text)


DATA_LABELS = ['018.DATA', '018.NOISE']


@pytest.fixture(scope='module')
def smoothing(cubeviz_layout):
    cl = cubeviz_layout

    sm = SelectSmoothing(cl._data, parent=cl)

    return sm


def assert_red_stylesheet(widget):
    assert widget.styleSheet() == "color: rgba(255, 0, 0, 128)"

@pytest.mark.parametrize("x", [0,1,2,3,4,5])
def test_smoothing(qtbot, cubeviz_layout, x):
    print("+++++++++++++++++++++++++++++++", x)
    # Create GUI
    sm = smoothing(cubeviz_layout)
    sm.k_size.setText("1")
    sm.combo.setCurrentIndex(x)         # Kernel Type
    sm.component_combo.setCurrentIndex(0)       # Data componenet

    print(sm.combo.currentText())
    print(sm.component_combo.currentText())

    # Call smoothing
    sm.call_main()
    sm.smooth_cube.thread.wait(2*60*1000)
    qtbot.keyPress(sm.abort_window.info_box, QtCore.Qt.Key_Enter)

    # Get Smoothed data
    smoothed_name = "018.DATA_Smoothed(" + sm.combo.currentText() + ", " + sm.component_combo.currentText()
    print("Smoothed name", smoothed_name)
    smoothing_component_id = [str(x) for x in cubeviz_layout._data.main_components if str(x).startswith(smoothed_name)]
    if isinstance(smoothing_component_id, list) and len(smoothing_component_id) > 0:
        smoothing_component_id = smoothing_component_id[0]
    else:
        return
    print("smoothing component id ", smoothing_component_id)
    np_result = np.asarray(cubeviz_layout._data[smoothing_component_id])

    # Get expected results
    cube = sm.smooth_cube.data_to_cube()
    if "median" == sm.smooth_cube.kernel_type:
        if "spatial" == sm.smooth_cube.smoothing_axis:
            new_cube = cube.spatial_smooth_median(sm.smooth_cube.kernel_size)
        else:
            new_cube = cube.spectral_smooth_median(sm.smooth_cube.kernel_size)
    else:
        kernel = sm.smooth_cube.get_kernel()
        if "spatial" == sm.smooth_cube.smoothing_axis:
            new_cube = cube.spatial_smooth(kernel)
        else:
            new_cube = cube.spectral_smooth(kernel)
    expected_result = new_cube._data


    #expected_result = np.asarray(sm.smooth_cube.smooth_cube).data
    print("NP results\n", np_result, "\nExpected results", expected_result, dir(expected_result))

    assert np.allclose(np_result, expected_result, rtol=0.01, equal_nan=True)



    # smooth_data = sm.data  # Glue data to be smoothed
    # smooth_smoothing_axis = sm.current_axis  # spectral vs spatial
    # smooth_kernel_type = sm.combo.currentText()  # Type of kernel, a key in kernel_registry
    # smooth_kernel_size = sm.k_size.current_text()  # Size of kernel in pix
    # smooth_component_id = sm.component_id  # Glue data component to smooth over
    # smooth_component_unit = sm.data.get_component(sm.component_id).units  # Units of component
    # smooth_output_label = sm.output_data_name()  # Output label
    # smooth_output_as_component = sm.smooth_cube.output_as_component  # Add output component to smooth_data
    # smooth_kernel_registry = sm.smooth_cube.get_kernel_registry()  # A list of kernels and params


    # smoothing_component_index = cubeviz_layout._data.main_components.index(smoothing_component_id)
    # smoothing_component_index = np.where(cubeviz_layout._data.main_components == smoothing_component_id)

    # smoothing_component_index = [i for i in range(len(cubeviz_layout._data.main_components)) if str(cubeviz_layout._data.main_components[i]) == str(smoothing_component_id)][0]
    #
    # for ind in range(len(cubeviz_layout._data.main_components)):
    #     if str(cubeviz_layout._data.main_components[ind]) == str(smoothing_component_id):
    #         print(ind, cubeviz_layout._data.main_components[ind], smoothing_component_id)
    #
    # print("smoothing component index ", smoothing_component_index)

    # print("************************************************\n", cubeviz_layout._data[smoothing_component_id], "\n", type(np_result.parent), dir(np_result.parent))







    #qtbot.mouseClick(sm.abort_window.info_box, QtCore.Qt.LeftButton)
    # qtbot.keyPress(cubeviz_layout, QtCore.Qt.Key_Enter)

    # for checki in range(5):
    #     print("Checking for smoothed", checki)
    #     if any([str(x).startswith('0.18.DATA_Smoothed') for x in cubeviz_layout._data.container_2d.component_ids()]):
    #         break
    #     else:
    #         time.sleep(5)
    #
    # if checki == 19:
    #     assert False, 'Could not find smoothing compennt'

    # qtbot.mouseClick(sm.abort_window.info, QtCore.Qt.LeftButton)

    # print(cubeviz_layout._data, hasattr(cubeviz_layout._data, "container_2d"), cubeviz_layout._data.container_2d.component_ids())
    # if hasattr(cubeviz_layout._data, "container_2d"):
    #     for i in cubeviz_layout._data.container_2d.component_ids():
    #         print(str(i))
    # smoothing_component_id = [str(x) for x in cubeviz_layout._data.container_2d.component_ids() if str(x).startswith('018.DATA_Smooth')][0]
    # np_result = cubeviz_layout._data.container_2d[smoothing_component_id]
    # print(np_result)

    # # Expected result
    # np_data = cubeviz_layout._data["018.DATA_Smoothed(Airy Disk, Spatial, 1.0_spaxel)"]
    #print("Smoothed should be here", cubeviz_layout._data.main_components, dir(cubeviz_layout._data))
    # np_data = cubeviz_layout._data[2]
    # print(np_data)
    # import spectral_cube
    # cube = spectral_cube.SpectralCube(np_data, wcs=cubeviz_layout._data.coords.wcs)
    # order = int(sm.order_combobox.currentText())
    # cube_moment = np.asarray(cube.moment(order=order, axis=0))

    # assert np.allclose(np_result, np_result, atol=1.0, equal_nan=True)
