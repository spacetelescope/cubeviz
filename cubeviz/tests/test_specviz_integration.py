"""
Contains tests of integration between specviz and cubeviz

In general, most of these tests should be in the specviz->cubeviz direction. In
other words, it should test whether events in specviz cause the appropriate
response in cubeviz. Tests in the other direction are probably better off being
added to existing cubeviz tests.
"""

import pytest
from glue.core import roi


@pytest.mark.parametrize('slice_index', [0, 100, 1000, 1024])
def test_specviz_slice_update(cubeviz_layout, slice_index):
    """
    Make sure slice updates in specviz propagate to cubeviz.
    """
    specviz = cubeviz_layout.specviz._widget
    wavelength = cubeviz_layout._slice_controller._wavelengths[slice_index]

    specviz._slice_indicator.setPos([wavelength, 0])
    assert cubeviz_layout._slice_controller.synced_index == slice_index


def test_cubeviz_roi(cubeviz_layout):
    """
    Test whether ROI creation in cubeviz propagates to specviz
    """
    specviz = cubeviz_layout.specviz._widget
    assert len(specviz._layer_artist_container.layers) == 1

    # Create ROI/subset
    cl_viewer = cubeviz_layout.split_views[1]._widget
    cl_viewer.apply_roi(roi.CircularROI(xc=6, yc=10, radius=3))

    assert len(specviz._layer_artist_container.layers) == 2

    # Remove the ROI/subset
    dc = cubeviz_layout.session.application.data_collection
    dc.remove_subset_group(dc.subset_groups[0])

    assert len(specviz._layer_artist_container.layers) == 1


def test_wavelength_units_update(cubeviz_layout):
    """
    Make sure wavelength unit changes in specviz are reflected in cubeviz.
    """
    specviz = cubeviz_layout.specviz._widget
    current_units = str(cubeviz_layout._wavelength_controller.current_units)

    specviz.hub.plot_widget.set_spectral_axis_unit('Angstrom')
    assert cubeviz_layout._wavelength_controller.current_units == 'Angstrom'

    specviz.hub.plot_widget.set_spectral_axis_unit(current_units)
    assert cubeviz_layout._wavelength_controller.current_units == current_units


def test_flux_units_update(cubeviz_layout):
    """
    Make sure flux unit changes in specviz are reflected in cubeviz
    """
    specviz = cubeviz_layout.specviz._widget

    component_id = cubeviz_layout.data_components[0]
    component = cubeviz_layout._data.get_component(component_id)
    current_units = component.units

    specviz.hub.plot_widget.set_data_unit('mJy')
    assert component.units == 'mJy'

    specviz.hub.plot_widget.set_data_unit(current_units)
    assert component.units == current_units
