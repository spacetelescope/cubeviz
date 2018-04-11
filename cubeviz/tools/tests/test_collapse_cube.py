# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

import pytest
import numpy as np

from qtpy import QtCore
from glue.core import roi
from cubeviz.tools.collapse_cube import CollapseCube

from ...tests.helpers import (toggle_viewer, select_viewer, left_click,
                      left_button_press, right_button_press, enter_slice_text,
                      assert_all_viewer_indices, assert_slice_text)


DATA_LABELS = ['018.DATA', '018.NOISE']


@pytest.fixture(scope='module')
def collapse_cube(cubeviz_layout):
    cl = cubeviz_layout

    wavelengths = cubeviz_layout._wavelength_controller.wavelengths
    wavelength_units = cubeviz_layout._wavelength_controller._current_units

    cc = CollapseCube(wavelengths, wavelength_units, cl._data, parent=cl)

    return cc


def assert_red_stylesheet(widget):
    assert widget.styleSheet() == "color: rgba(255, 0, 0, 128)"


def test_collapse_ui(qtbot, collapse_cube):

    cc = collapse_cube
    cc.ui.start_input.setText('a')
    qtbot.mouseClick(cc.ui.calculate_button, QtCore.Qt.LeftButton)
    assert_red_stylesheet(cc.ui.start_label)

    cc.ui.start_input.setText('100')
    cc.ui.end_input.setText('50')
    qtbot.mouseClick(cc.ui.calculate_button, QtCore.Qt.LeftButton)
    assert_red_stylesheet(cc.ui.start_label)

    # "reset" the values
    cc.ui.start_input.setText('0')
    cc.ui.end_input.setText('1')

    # Negative simple sigma value
    cc.ui.sigma_combobox.setCurrentIndex(1)
    cc.ui.simple_sigma_input.setText('-10')
    qtbot.mouseClick(cc.ui.calculate_button, QtCore.Qt.LeftButton)
    assert_red_stylesheet(cc.ui.simple_sigma_label)

    # Negative advanced sigma value
    cc.ui.sigma_combobox.setCurrentIndex(2)
    cc.ui.advanced_sigma_input.setText('-10')
    qtbot.mouseClick(cc.ui.calculate_button, QtCore.Qt.LeftButton)
    assert_red_stylesheet(cc.ui.advanced_sigma_label)

    # Negative advanced sigma value
    cc.ui.sigma_combobox.setCurrentIndex(2)
    cc.ui.advanced_sigma_input.setText('3')
    cc.ui.advanced_sigma_lower_input.setText('2')
    cc.ui.advanced_sigma_upper_input.setText('1')
    qtbot.mouseClick(cc.ui.calculate_button, QtCore.Qt.LeftButton)
    assert_red_stylesheet(cc.ui.advanced_sigma_lower_label)
    assert_red_stylesheet(cc.ui.advanced_sigma_upper_label)

def test_starting_state(cubeviz_layout):

    cc = collapse_cube(cubeviz_layout)

    # No clipping
    data_name = DATA_LABELS[0]
    operation = 'Sum'
    spatial_region = 'Image'
    start_index = 100
    end_index = 300
    sigma_selection = 'No Sigma Clipping'
    sigma_parameter = None

    new_wavelengths, new_component, label = cc._calculate_collapse(data_name,
            operation, spatial_region, sigma_selection, sigma_parameter, start_index, end_index)

    assert label == '018.DATA-collapse-Sum (1.9531e-06, 2.0092e-06)'

    output = np.array([[0, 0, 0, 0], [139.281, 1088, 844.167, 739.379]])
    assert np.allclose(new_component[:2,:4], output, atol=1)


    # Simple Sigma Clipping
    data_name = DATA_LABELS[0]
    operation = 'Sum'
    spatial_region = 'Image'
    start_index = 300
    end_index = 400
    sigma_selection = 'Simple Sigma Clipping'
    sigma_parameter = 3.0

    new_wavelengths, new_component, label = cc._calculate_collapse(data_name,
            operation, spatial_region, sigma_selection, sigma_parameter, start_index, end_index)

    assert label == '018.DATA-collapse-Sum (2.0092e-06, 2.0373e-06) sigma=3.0'

    output = np.array([[0, 0, 0, 0], [845.868, 886.972, 726.566, 976.271]])
    assert np.allclose(new_component[:2,:4], output, atol=1)

    # Advanced Sigma Clipping
    data_name = DATA_LABELS[0]
    operation = 'Sum'
    spatial_region = 'Image'
    start_index = 300
    end_index = 400
    sigma_selection = 'Advanced Sigma Clipping'
    sigma_parameter = [3.0, 1.0, 4.0, 2]

    new_wavelengths, new_component, label = cc._calculate_collapse(data_name,
            operation, spatial_region, sigma_selection, sigma_parameter, start_index, end_index)

    assert label == '018.DATA-collapse-Sum (2.0092e-06, 2.0373e-06) sigma=3.0 sigma_lower=1.0 sigma_upper=4.0 sigma_iters=2'

    output = np.array([[0, 0, 0, 0], [867.687, 956.132, 775.984, 1008]])
    assert np.allclose(new_component[:2,:4], output, atol=1)

def test_regions(qtbot, cubeviz_layout):

    viewer = cubeviz_layout.split_views[0]._widget
    # Create a pretty arbitrary circular ROI
    viewer.apply_roi(roi.CircularROI(xc=6, yc=10, radius=3))

    cc = collapse_cube(cubeviz_layout)

    start_index = 682
    end_index = 1364

    # Set the values and do the calculation through the GUI
    cc.ui.data_combobox.setCurrentIndex(0)
    cc.ui.operation_combobox.setCurrentIndex(0)
    cc.ui.spatial_region_combobox.setCurrentIndex(1)
    cc.ui.region_combobox.setCurrentIndex(1) # indices
    cc.ui.start_input.setText('{}'.format(start_index))
    cc.ui.end_input.setText('{}'.format(end_index))
    cc.ui.sigma_combobox.setCurrentIndex(0)
    qtbot.mouseClick(cc.ui.calculate_button, QtCore.Qt.LeftButton)

    # Calculate what we expect
    np_data = cubeviz_layout._data[DATA_LABELS[0]]
    mask = cubeviz_layout._data.subsets[0].to_mask()
    np_data_sum = np.sum(np_data[start_index:end_index]*mask[start_index:end_index], axis=0)

    # Get the result
    collapse_component_id = [str(x) for x in cubeviz_layout._data.container_2d.component_ids() if str(x).startswith('018.DATA-collap')][0]
    np_result = cubeviz_layout._data.container_2d[collapse_component_id]

    # Delete the ROI first, in case the assert fails
    dc = cubeviz_layout.session.application.data_collection
    dc.remove_subset_group(dc.subset_groups[0])

    print('combo box items {}'.format([cc.ui.operation_combobox.itemText(i) for i in range(cc.ui.operation_combobox.count())]))
    print('combo box selected {}'.format(cc.ui.operation_combobox.currentText()))
    print('np_data_sum {}'.format(np_data_sum))
    print('np_result {}'.format(np_result))
    assert np.allclose(np_data_sum, np_result, atol=1.0)
