# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

import pytest
import numpy as np

from cubeviz.tools.moment_maps import MomentMapsGUI

from .helpers import (toggle_viewer, select_viewer, left_click,
                      left_button_press, right_button_press, enter_slice_text,
                      assert_all_viewer_indices, assert_slice_text)


DATA_LABELS = ['018.DATA', '018.NOISE']


@pytest.fixture(scope='module')
def moment_map(cubeviz_layout):
    cl = cubeviz_layout
    mm_gui = MomentMapsGUI(cl._data, cl.session.data_collection, parent=cl)
    mm_gui.do_calculation(1, DATA_LABELS[0])

    return mm_gui.label

def test_starting_state(cubeviz_layout):
    assert cubeviz_layout.isVisible() == True

    assert cubeviz_layout._single_viewer_mode == False
    assert cubeviz_layout._active_view is cubeviz_layout.left_view
    assert cubeviz_layout._active_cube is cubeviz_layout.left_view

    for viewer in cubeviz_layout.all_views:
        assert viewer._widget.synced == True

def assert_active_view_and_cube(layout, viewer):
    assert layout._active_view is viewer
    assert layout._active_cube is viewer

def test_active_viewer(qtbot, cubeviz_layout):
    select_viewer(qtbot, cubeviz_layout.middle_view)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.middle_view)

    select_viewer(qtbot, cubeviz_layout.right_view)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.right_view)

    select_viewer(qtbot, cubeviz_layout.specviz)
    assert cubeviz_layout._active_view is cubeviz_layout.specviz
    # Selecting the specviz viewer should not affect the last active cube
    assert cubeviz_layout._active_cube is cubeviz_layout.right_view

    select_viewer(qtbot, cubeviz_layout.left_view)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.left_view)

def test_toggle_viewer_mode(qtbot, cubeviz_layout):
    toggle_viewer(qtbot, cubeviz_layout)
    assert cubeviz_layout._single_viewer_mode == True
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.single_view)

    toggle_viewer(qtbot, cubeviz_layout)
    assert cubeviz_layout._single_viewer_mode == False
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.left_view)

def test_remember_active_viewer(qtbot, cubeviz_layout):
    """Make sure that the active viewer in the current layout is remembered"""

    # Change active viewer in the split mode viewer
    select_viewer(qtbot, cubeviz_layout.right_view)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.right_view)

    # Change to the single mode viewer
    toggle_viewer(qtbot, cubeviz_layout)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.single_view)
    # Change active viewer in the single mode viewer
    select_viewer(qtbot, cubeviz_layout.specviz)
    assert cubeviz_layout._active_view == cubeviz_layout.specviz
    assert cubeviz_layout._active_cube == cubeviz_layout.single_view

    # Change back to the split mode viewer
    toggle_viewer(qtbot, cubeviz_layout)
    assert_active_view_and_cube(cubeviz_layout, cubeviz_layout.right_view)

    # Change back to the single mode viewer
    toggle_viewer(qtbot, cubeviz_layout)
    assert cubeviz_layout._active_view == cubeviz_layout.specviz
    assert cubeviz_layout._active_cube == cubeviz_layout.single_view

@pytest.mark.parametrize('viewer_index', [0, 1, 2, 3])
def test_sync_checkboxes(qtbot, cubeviz_layout, viewer_index):
    """This test simply makes sure that the checkbox changes the synced state
    of the corresponding viewer. It does not test the effects of syncing on the
    viewer indices.
    """
    # When testing the single viewer checkbox, first toggle to single viewer mode
    if viewer_index == 0:
        toggle_viewer(qtbot, cubeviz_layout)

    checkbox = cubeviz_layout._synced_checkboxes[viewer_index]
    viewer = cubeviz_layout.all_views[viewer_index]

    left_click(qtbot, checkbox)
    assert viewer._widget.synced == False

    left_click(qtbot, checkbox)
    assert viewer._widget.synced == True

def check_data_component(layout, combo, index, widget):
    combo.setCurrentIndex(index)
    current_label = DATA_LABELS[index]
    assert combo.currentText() == current_label
    np.testing.assert_allclose(
        widget.layers[0].state.get_sliced_data(),
        layout._data[current_label][layout.synced_index])

def setup_combo_and_index(qtbot, layout, index):
    if index == 0:
        toggle_viewer(qtbot, layout)
        combo = getattr(layout.ui, 'single_viewer_combo')
        current_index = 0
    else:
        combo = getattr(layout.ui, 'viewer{0}_combo'.format(index))
        current_index = index - 1

    return combo, current_index

@pytest.mark.parametrize('viewer_index', [0, 1, 2, 3])
def test_viewer_dropdowns(qtbot, cubeviz_layout, viewer_index):
    combo, current_index = setup_combo_and_index(
                                qtbot, cubeviz_layout, viewer_index)
    if viewer_index == 0:
        toggle_viewer(qtbot, cubeviz_layout)
        combo = getattr(cubeviz_layout.ui, 'single_viewer_combo')
        current_index = 0
    else:
        combo = getattr(cubeviz_layout.ui, 'viewer{0}_combo'.format(viewer_index))
        current_index = min(viewer_index - 1, 1) # only two datasets

    widget = cubeviz_layout.all_views[viewer_index]._widget

    # Make sure there are only two data components currently (dataset has two)
    assert combo.count() == 2
    # Make sure starting index is set appropriately
    assert combo.currentIndex() == current_index

    for i in range(2):
        current_index = (current_index + 1) % 2
        check_data_component(cubeviz_layout, combo, current_index, widget)

def test_add_data_component(qtbot, cubeviz_layout):
    new_label = 'QuirkyLabel'
    new_data = np.random.random(cubeviz_layout._data.shape)
    cubeviz_layout._data.add_component(new_data, new_label)

    for viewer_index in range(4):
        combo, current_index = setup_combo_and_index(
                                    qtbot, cubeviz_layout, viewer_index)
        widget = cubeviz_layout.all_views[viewer_index]._widget

        # Make sure the new index is there
        assert combo.count() == 3
        # Make sure the index hasn't changed (this might behave differently in the future)
        #assert combo.currentIndex() == current_index

        # Make sure none of the original components have changed
        for i in range(2):
            check_data_component(cubeviz_layout, combo, i, widget)

        # Make sure the new data is displayed when selected
        combo.setCurrentIndex(2)
        assert combo.currentText() == new_label
        np.testing.assert_allclose(
            widget.layers[0].state.get_sliced_data(),
            cubeviz_layout._data[new_label][cubeviz_layout.synced_index])

        # Toggle back to split viewer mode if necessary
        if viewer_index == 0:
            toggle_viewer(qtbot, cubeviz_layout)

def test_key_shortcuts(qtbot, cubeviz_layout):
    slice_val = cubeviz_layout._slice_controller._slice_slider.value()
    left_button_press(qtbot, cubeviz_layout)
    assert cubeviz_layout._slice_controller._slice_slider.value() == slice_val - 1
    right_button_press(qtbot, cubeviz_layout)
    assert cubeviz_layout._slice_controller._slice_slider.value() == slice_val
    right_button_press(qtbot, cubeviz_layout)
    assert cubeviz_layout._slice_controller._slice_slider.value() == slice_val + 1

def assert_slider_enabled(cubeviz_layout, enabled):
    assert cubeviz_layout._slice_controller._slice_slider.isEnabled() == enabled
    assert cubeviz_layout._slice_controller._slice_textbox.isEnabled() == enabled
    assert cubeviz_layout._slice_controller._wavelength_textbox.isEnabled() == enabled

@pytest.mark.parametrize('while_active', [True, False])
def test_2d_data_components(qtbot, cubeviz_layout, moment_map, while_active):
    """This test ensures that the slider behaves as expected when 2D data
    components are present. It tests updating the viewer containing 2D data
    both while it is the active viewer and while it is not the active
    viewer."""

    assert moment_map == DATA_LABELS[0] + '-moment-1'

    assert_slider_enabled(cubeviz_layout, True)

    combo, _ = setup_combo_and_index(qtbot, cubeviz_layout, 1)
    combo.setCurrentIndex(combo.findText(moment_map))

    assert_slider_enabled(cubeviz_layout, False)
    assert cubeviz_layout.left_view._widget.has_2d_data == True
    assert cubeviz_layout.left_view._widget.synced == False

    # Change the active viewer and make sure the slider is re-enabled
    select_viewer(qtbot, cubeviz_layout.middle_view)
    assert_slider_enabled(cubeviz_layout, True)

    enter_slice_text(qtbot, cubeviz_layout, 1234)

    # Change back to the left viewer currently displaying 2D data
    if while_active:
        select_viewer(qtbot, cubeviz_layout.left_view)
        assert cubeviz_layout.left_view._widget.has_2d_data == True
        assert cubeviz_layout.left_view._widget.synced == False

    # Return to displaying 3D data component
    combo.setCurrentIndex(combo.findText(DATA_LABELS[0]))
    assert_all_viewer_indices(cubeviz_layout, 1234)
    assert cubeviz_layout.left_view._widget.has_2d_data == False
    assert cubeviz_layout.left_view._widget.synced == True

    if not while_active:
        select_viewer(qtbot, cubeviz_layout.left_view)
        assert_slider_enabled(cubeviz_layout, True)

    assert_slider_enabled(cubeviz_layout, True)
    assert_slice_text(cubeviz_layout, 1234)
