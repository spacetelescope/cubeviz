"""
Contains tests of integration between specviz and cubeviz

In general, most of these tests should be in the specviz->cubeviz direction. In
other words, it should test whether events in specviz cause the appropriate
response in cubeviz. Tests in the other direction are probably better off being
added to existing cubeviz tests.
"""

import pytest


@pytest.mark.parametrize('slice_index', [0, 100, 1000, 1024])
def test_specviz_slice_update(cubeviz_layout, slice_index):
    """
    Make sure slice updates in specviz propagate to cubeviz.
    """
    specviz = cubeviz_layout.specviz._widget
    wavelength = cubeviz_layout._slice_controller._wavelengths[slice_index]

    specviz._slice_indicator.setPos([wavelength, 0])
    assert cubeviz_layout._slice_controller.synced_index == slice_index
