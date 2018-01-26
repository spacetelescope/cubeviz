from astropy import units as u


class UnitController:
    def __init__(self, cubeviz_layout):
        self._cv_layout = cubeviz_layout
        ui = cubeviz_layout.ui
        self._original_wavelengths = self._cv_layout._wavelengths
        self._new_wavelengths = []
        self._original_units = u.m
        self._new_units = u.m
        self._wcs = None

        # This is the Wavelength conversion/combobox code
        self._wavelength_combobox = ui.unitcomboBox
        self.units = [u.m, u.cm, u.mm, u.um, u.nm, u.Angstrom]
        self.units_titles = list(u.long_names[0].title() for u in self.units)
        self._wavelength_combobox.addItems(self.units_titles)

        self._wavelength_combobox.activated.connect(self._on_combobox_change)

        # This is the label for the wavelength units
        self._wavelength_textbox_label = ui.wavelength_textbox_label

    def _on_combobox_change(self, event):
        """
        Callback for change in unitcombobox value
        :param event:
        :return:
        """
        # Get the new unit name from the selected value in the comboBox and
        # set that as the new unit that wavelengths will be converted to
        new_unit_name = self._wavelength_combobox.currentText()
        self._new_units = self.units[self.units_titles.index(new_unit_name)]

        self._new_wavelengths = self.convert_wavelengths(self._original_wavelengths, self._original_units, self._new_units)
        if self._new_wavelengths is None:
            return

        # Set layout._wavelength as the new wavelength
        self._cv_layout.set_wavelengths(self._new_wavelengths, self._new_units)

    def convert_wavelengths(self, old_wavelengths, old_units, new_units):
        if old_wavelengths is not None:
            new_wavelengths = ((old_wavelengths * old_units).to(new_units) / new_units)
            return new_wavelengths
        return False

    def enable(self, wcs, wavelength):
        self._original_wavelengths = wavelength
        self._wcs = wcs
        print(str(wcs.wcs.cunit[2]))