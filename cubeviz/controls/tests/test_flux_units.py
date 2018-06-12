import pytest
from qtpy import QtCore

import numpy as np
from astropy import units as u

from ...tests.helpers import (enter_slice_text, enter_wavelength_text,
                              left_click, select_viewer, enter_slice_text,
                              toggle_viewer, assert_viewer_indices,
                              assert_all_viewer_indices,
                              assert_wavelength_text, assert_slice_text)

from ..flux_units import CubeVizUnit, FluxUnitController


def add_get_remove_units(cubeviz_layout, flux_unit_controller=None):
    data = cubeviz_layout._data
    if flux_unit_controller is None:
        flux_unit_controller = FluxUnitController(cubeviz_layout)
        flux_unit_controller.set_data(data)

    component_ids = data.component_ids()
    for component_id in component_ids:
        flux_unit_controller[component_id] = u.Jy

    for component_id in component_ids:
        del flux_unit_controller[component_id]

    for component_id in component_ids:
        flux_unit_controller.add_component_unit(component_id, u.Jy)

    for component_id in component_ids:
        unit = flux_unit_controller.get_component_unit(component_id)
        assert (unit == u.Jy)
        unit = flux_unit_controller.get_component_unit(component_id, cubeviz_unit=True)
        assert (unit.unit == u.Jy)
        unit = flux_unit_controller[component_id]
        assert (unit.unit == u.Jy)

    for component_id in component_ids:
        flux_unit_controller.remove_component_unit(component_id)

    assert (len(flux_unit_controller.components) == 0)


def test_flux_unit_controller(qtbot, cubeviz_layout):
    # test flux controller creation
    flux_unit_controller = FluxUnitController(cubeviz_layout)

    # Test conversion
    cvu = CubeVizUnit(u.Unit("1e-17 erg/s/cm2/Angstrom"),
                      "1e-17 erg/s/cm2/Angstrom",
                      "FLUX",
                      "ASTROPY")

    cvu.controller = flux_unit_controller

    # Set units to something else
    cvu.unit = u.uJy

    wave = 5000 * u.Angstrom
    result = cvu.convert_value(5.0, wave=wave)

    assert(np.allclose(41.69551, result))

    # Test adding, getting and removing units
    # 1) To empty flux unit controller
    add_get_remove_units(cubeviz_layout)

    # 2) To the controller in the layout
    add_get_remove_units(cubeviz_layout, cubeviz_layout._flux_unit_controller)
