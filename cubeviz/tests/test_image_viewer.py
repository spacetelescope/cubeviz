import pytest
import numpy as np
from glue.core import roi

from cubeviz.utils.contour import ContourSettings
from cubeviz.tools.moment_maps import MomentMapsGUI


@pytest.fixture(scope='module')
def moment_maps_gui(cubeviz_layout):
    cl = cubeviz_layout

    mm = MomentMapsGUI(cl._data, cl.session.data_collection, parent=cl)

    return mm


def test_stats_box_without_subset(cubeviz_layout):
    """
    Tests the stat box underneath the ImageViewer when it is the full spectrum
    """
    cl_viewer = cubeviz_layout.split_views[1]._widget

    cl_viewer._subset = None

    data = cl_viewer._data[0][cl_viewer.current_component_id][cl_viewer._slice_index]

    wave = cl_viewer.cubeviz_layout.get_wavelength(cl_viewer.slice_index)
    data_wave = cl_viewer.cubeviz_unit.convert_value(data, wave=wave)

    assert data_wave is not None

    results = (np.nanmin(data_wave), np.nanmax(data_wave), np.median(data_wave), data_wave.mean(), data_wave.std())
    results_string = r"min={:.4}, max={:.4}, median={:.4}, μ={:.4}, σ={:.4}".format(*results)

    assert results_string == cl_viewer.parent().stats_text.text()


def test_stats_box_with_subset(cubeviz_layout):
    """
    Tests the stat box underneath the ImageViewer when there is an ROI
    """
    cl_viewer = cubeviz_layout.split_views[1]._widget

    # Create a subset (ROI) if there is none
    cl_viewer.apply_roi(roi.CircularROI(xc=6, yc=10, radius=3))

    assert cl_viewer._subset is not None

    mask = cl_viewer._subset.to_mask()[cl_viewer._slice_index]
    data = cl_viewer._data[0][cl_viewer.current_component_id][cl_viewer._slice_index][mask]

    wave = cl_viewer.cubeviz_layout.get_wavelength(cl_viewer.slice_index)
    data_wave = cl_viewer.cubeviz_unit.convert_value(data, wave=wave)

    assert data_wave is not None

    results = (np.nanmin(data_wave), np.nanmax(data_wave), np.median(data_wave), data_wave.mean(), data_wave.std())
    results_string = r"min={:.4}, max={:.4}, median={:.4}, μ={:.4}, σ={:.4}".format(*results)

    assert results_string == cl_viewer.parent().stats_text.text()

    # Remove the ROI/subset
    dc = cubeviz_layout.session.application.data_collection
    dc.remove_subset_group(dc.subset_groups[0])


def test_overlay(moment_maps_gui, cubeviz_layout):
    # Only "No Overlay" option available in combobox
    assert cubeviz_layout._overlay_controller._overlay_image_combo.count() == 1

    # Create moment map GUI
    mm = moment_maps_gui
    mm.display()
    mm.order_combobox.setCurrentIndex(0)
    mm.data_combobox.setCurrentIndex(0)

    # Call calculate function and get result
    mm.calculateButton.click()

    # Second option in combobox for moment map overlay
    assert cubeviz_layout._overlay_controller._overlay_image_combo.count() == 2

    cl_viewer = cubeviz_layout.split_views[1]._widget
    assert len(cl_viewer.axes.images) == 1

    # Set overlay and check changing of settings works
    cubeviz_layout._overlay_controller._overlay_image_combo.setCurrentIndex(1)
    cubeviz_layout._overlay_controller._overlay_colormap_combo.setCurrentIndex(10)
    cubeviz_layout._overlay_controller._alpha_slider.setValue(50)

    assert len(cl_viewer.axes.images) == 2

    # Return to "No Overlay"
    cubeviz_layout._overlay_controller._overlay_image_combo.setCurrentIndex(0)

    assert len(cl_viewer.axes.images) == 1

    # Remove the moment map data set
    for helper in cubeviz_layout._viewer_combo_helpers:
        helper.remove_data(cubeviz_layout._data.container_2d)
    for cid in cubeviz_layout._data.container_2d.component_ids():
        cubeviz_layout._data.container_2d.remove_component(cid)
    del cubeviz_layout._data.container_2d
    dc = cubeviz_layout.session.data_collection
    dc.remove(dc[1])

def check_viewer_title(cubeviz_layout, viewer_idx, component_idx):
    viewer = cubeviz_layout.cube_views[viewer_idx]._widget

    combo = cubeviz_layout.get_viewer_combo(viewer_idx)
    combo.setCurrentIndex(component_idx)

    component_id = cubeviz_layout.data_components[component_idx]
    component = cubeviz_layout._data.get_component(component_id)

    title = '{} [{}]'.format(component_id, component.units)
    assert viewer.axes.title.get_text() == title


def test_viewer_title(cubeviz_layout):
    """
    Test whether viewer titles accurately reflect data component and flux unit
    """
    for idx in range(len(cubeviz_layout.cube_views[1:])):
        combo = cubeviz_layout.get_viewer_combo(idx)
        current_idx = combo.currentIndex()

        check_viewer_title(cubeviz_layout, idx, 0)
        check_viewer_title(cubeviz_layout, idx, 1)

        # Reset the combo when we're done
        combo = cubeviz_layout.get_viewer_combo(idx)
        combo.setCurrentIndex(current_idx)


def test_viewer_flux_units_change(cubeviz_layout):
    """
    Test whether viewer titles update appropriately with flux unit changes
    """
    # Test after flux units change
    specviz = cubeviz_layout.specviz._widget
    current_units = specviz.hub.plot_widget.data_unit
    specviz.hub.plot_widget.set_data_unit('mJy')

    for idx in range(len(cubeviz_layout.cube_views)):
        combo = cubeviz_layout.get_viewer_combo(idx)
        current_idx = combo.currentIndex()

        check_viewer_title(cubeviz_layout, idx, 0)

        # Check whether the flux units associated with this viewer is correct.
        # This is reflected in the mouseover display of flux values
        assert cubeviz_layout.cube_views[idx]._widget.cubeviz_unit.unit == 'mJy'

        # Reset the combo when we're done
        combo = cubeviz_layout.get_viewer_combo(idx)
        combo.setCurrentIndex(current_idx)

    # Restore original units
    specviz.hub.plot_widget.set_data_unit(current_units)


def test_viewer_wavelength_units_change(cubeviz_layout):
    """
    Test whether image viewer wavelength units are updated appropriately

    These units are used by the viewer to populate the viewer status bar during
    mouseover.
    """

    current_units = str(cubeviz_layout._wavelength_controller.current_units)

    for viewer in cubeviz_layout.cube_views:
        assert viewer._widget._wavelength_units == current_units

    specviz = cubeviz_layout.specviz._widget
    specviz.hub.plot_widget.set_spectral_axis_unit('Angstrom')

    for viewer in cubeviz_layout.cube_views:
        assert viewer._widget._wavelength_units == 'Angstrom'

    # Restore original wavelength units
    specviz.hub.plot_widget.set_spectral_axis_unit(current_units)


def test_default_contour(cubeviz_layout):
    """
    Make sure that default contour works
    """
    # Keep track of children in viewer to check that number increases later
    cl_viewer = cubeviz_layout.split_views[1]._widget
    cl_viewer_children = len(cl_viewer.axes.get_children())

    # Create a subset (ROI) if there is none
    cl_viewer.apply_roi(roi.CircularROI(xc=6, yc=10, radius=3))
    cl_viewer.default_contour()

    assert len(cl_viewer.axes.get_children()) > cl_viewer_children
    assert cl_viewer.is_contour_active

    cl_viewer.remove_contour()

    # Remove the ROI/subset
    dc = cubeviz_layout.session.application.data_collection
    dc.remove_subset_group(dc.subset_groups[0])

    assert cl_viewer.is_contour_active == False
    assert len(cl_viewer.axes.get_children()) == cl_viewer_children

def test_contour_preview(cubeviz_layout):
    """
    Create contour preview from code
    """
    # Keep track of children in viewer to check that number increases later
    cl_viewer = cubeviz_layout.split_views[1]._widget
    cl_viewer_children = len(cl_viewer.axes.get_children())

    preview_settings = ContourSettings(cl_viewer)
    preview_settings.default_options()

    cl_viewer.set_contour_preview(preview_settings)

    assert cl_viewer.is_contour_preview_active
    assert cl_viewer.contour_preview_settings == preview_settings
    assert len(cl_viewer.axes.get_children()) > cl_viewer_children

    cl_viewer.end_contour_preview()

    assert cl_viewer.is_contour_preview_active == False
    assert cl_viewer.contour_preview_settings is None
    assert len(cl_viewer.axes.get_children()) == cl_viewer_children

def test_change_contour_settings(cubeviz_layout):
    """
    Create default contour, open settings menu, change settings, press preview, press ok
    """
    # Keep track of children in viewer to check that number increases later
    cl_viewer = cubeviz_layout.split_views[1]._widget
    cl_viewer_children = len(cl_viewer.axes.get_children())

    cl_viewer.default_contour()
    assert cl_viewer.is_contour_active
    assert len(cl_viewer.axes.get_children()) > cl_viewer_children

    contour_dialog = cl_viewer.edit_contour_settings()

    # Set settings in dialog box
    contour_dialog.contour_label_checkBox.setChecked(True)
    contour_dialog.font_size_input.setText("12")

    contour_dialog.custom_spacing_checkBox.setChecked(True)
    contour_dialog.spacing_input.setText("1")

    contour_dialog.vmax_checkBox.setChecked(True)
    contour_dialog.vmax_input.setText("2")

    contour_dialog.vmin_checkBox.setChecked(True)
    contour_dialog.vmin_input.setText("1")

    contour_dialog.previewButton.click()
    assert cl_viewer.is_contour_preview_active

    contour_dialog.okButton.click()

    # Check to make sure setting changes went through
    assert contour_dialog.font_size_input.text() == "12"
    assert contour_dialog.spacing_input.text() == "1"
    assert contour_dialog.vmax_input.text() == "2"
    assert contour_dialog.vmin_input.text() == "1"

    assert cl_viewer.is_contour_preview_active == False

    cl_viewer.remove_contour()

    assert cl_viewer.is_contour_active == False
    assert len(cl_viewer.axes.get_children()) == cl_viewer_children
