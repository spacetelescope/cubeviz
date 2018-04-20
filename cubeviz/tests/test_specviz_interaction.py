# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

import pytest

from qtpy.QtCore import Qt

from glue.core import roi


def specviz_layer_visible(specviz_viewer, glue_layer):

    specviz_layer = specviz_viewer._specviz_data_cache[glue_layer]
    layer_item = specviz_viewer._layer_list.get_layer_item(specviz_layer)
    return layer_item.checkState(0) == Qt.Checked

def test_create_roi(cubeviz_layout):
    viewer = cubeviz_layout.split_views[0]._widget
    # Create a pretty arbitrary circular ROI
    viewer.apply_roi(roi.CircularROI(xc=10, yc=10, radius=5))
    assert len(cubeviz_layout._data.subsets) == 1

    subset = cubeviz_layout._data.subsets[0]
    specviz = cubeviz_layout.specviz._widget
    assert subset in specviz._specviz_data_cache
    assert len(specviz._specviz_data_cache) == 2

    layer = specviz._specviz_data_cache[subset]
    assert layer in specviz._layer_list.all_layers

    # Make sure the ROI layer is the only visible spectrum
    assert specviz_layer_visible(specviz, cubeviz_layout._data) == False
    assert specviz_layer_visible(specviz, subset) == True

def test_delete_roi(cubeviz_layout):
    # This test assumes that an ROI was created by the previous test
    dc = cubeviz_layout.session.application.data_collection
    dc.remove_subset_group(dc.subset_groups[0])
    assert len(cubeviz_layout._data.subsets) == 0

    specviz = cubeviz_layout.specviz._widget
    assert cubeviz_layout._data in specviz._specviz_data_cache
    assert len(specviz._specviz_data_cache) == 1

    layer = specviz._specviz_data_cache[cubeviz_layout._data]
    assert layer in specviz._layer_list.all_layers
    assert len(specviz._layer_list.all_layers) == 1

def test_update_units(cubeviz_layout):
    # This test checks for a bug that was previously in specviz that caused the
    # main spectrum to reappear after an update in flux units
    from astropy import units as u
    spaxel = u.def_unit('spaxel', u.astrophys.pix)
    u.add_enabled_units(spaxel)

    new_unit = u.milliJansky / spaxel

    class FakeCubevizUnit:
        unit = new_unit
        unit_string = new_unit.to_string()

    viewer = cubeviz_layout.split_views[0]._widget
    viewer.apply_roi(roi.CircularROI(xc=10, yc=10, radius=5))

    controller = cubeviz_layout._flux_unit_controller
    component_id = cubeviz_layout._data.find_component_id('018.DATA')
    controller.update_component_unit(component_id, FakeCubevizUnit)

    subset = cubeviz_layout._data.subsets[0]
    specviz = cubeviz_layout.specviz._widget
    assert subset in specviz._specviz_data_cache

    layer = specviz._specviz_data_cache[cubeviz_layout._data]
    assert layer in specviz._layer_list.all_layers

    assert specviz_layer_visible(specviz, cubeviz_layout._data) == False
    assert specviz_layer_visible(specviz, subset) == True

    # Delete the subset when we're done
    dc = cubeviz_layout.session.application.data_collection
    dc.remove_subset_group(dc.subset_groups[0])
