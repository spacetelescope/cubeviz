def test_update_specviz(cubeviz_layout):
    """
    Make sure wavelength unit update is reflected in specviz.
    """
    specviz = cubeviz_layout.specviz._widget
    current_units = str(cubeviz_layout._wavelength_controller.current_units)

    cubeviz_layout._wavelength_controller.update_units('Angstrom')
    assert specviz.hub.plot_widget.spectral_axis_unit == 'Angstrom'

    cubeviz_layout._wavelength_controller.update_units(current_units)
    assert specviz.hub.plot_widget.spectral_axis_unit == current_units
