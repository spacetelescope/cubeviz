import os
import yaml
import warnings

import numpy as np

from qtpy.QtCore import Qt, Signal, QThread
from qtpy.QtWidgets import (
    QDialog, QApplication, QPushButton, QProgressBar,
    QLabel, QWidget, QDockWidget, QHBoxLayout, QVBoxLayout,
    QComboBox, QMessageBox, QLineEdit, QRadioButton, QWidgetItem, QSpacerItem
)

from glue.utils.qt import update_combobox

from astropy.utils.exceptions import AstropyWarning
from astropy import units as u
from specviz.third_party.glue.data_viewer import dispatch as specviz_dispatch

OBS_WAVELENGTH_TEXT = 'Obs Wavelength'
REST_WAVELENGTH_TEXT = 'Rest Wavelength'

DEFAULT_FLUX_UNITS_CONFIGS = os.path.join(os.path.dirname(__file__), 'registered_flux_units.yaml')


class UnitController:
    def __init__(self, cubeviz_layout):
        self._cv_layout = cubeviz_layout
        ui = cubeviz_layout.ui
        self._original_wavelengths = self._cv_layout._wavelengths
        self._new_wavelengths = []
        self._original_units = u.m
        self._new_units = self._original_units
        self._wcs = None

        # Add the redshift z value
        self._redshift_z = 0

        # This is the Wavelength conversion/combobox code
        self._units = [u.m, u.cm, u.mm, u.um, u.nm, u.AA]
        self._units_titles = list(u.long_names[0].title() for u in self._units)

        # This is the label for the wavelength units
        self._wavelength_textbox_label = ui.wavelength_textbox_label.text()

        specviz_dispatch.setup(self)

    @property
    def wavelength_label(self):
        return self._wavelength_textbox_label

    @wavelength_label.setter
    def wavelength_label(self, value):
        self._wavelength_textbox_label = value

    @property
    def units(self):
        return self._units

    @property
    def unit_titles(self):
        return self._units_titles

    @property
    def redshift_z(self):
        """
        Get the Z value for the redshift.

        :return: Z redshift value
        """
        return self._redshift_z

    @redshift_z.setter
    def redshift_z(self, new_z):
        """
        Set the new Z value for the redshift.

        :return: Z redshift value
        """

        # We want to make sure there is no odd messaging looping that might
        # happen if we receive the same value. In this case, we are done.
        if self._redshift_z == new_z:
            return

        self._redshift_z = new_z

        if new_z is not None and new_z > 0:
            # Set the label
            self._wavelength_textbox_label = REST_WAVELENGTH_TEXT
            self._cv_layout._slice_controller.wavelength_label = REST_WAVELENGTH_TEXT
            self._cv_layout.set_wavelengths((1+new_z)*self._original_wavelengths, self._new_units)
        else:
            # Set the label
            self._wavelength_textbox_label = OBS_WAVELENGTH_TEXT
            self._cv_layout._slice_controller.wavelength_label = OBS_WAVELENGTH_TEXT
            self._cv_layout.set_wavelengths(self._original_wavelengths, self._new_units)

        # Calculate and set the new wavelengths
        self._wavelengths = self._original_wavelengths / (1 + self._redshift_z)

        # Send them to the slice controller
        self._cv_layout._slice_controller.set_wavelengths(self._wavelengths, self._new_units)

        # Send the redshift value to specviz
        specviz_dispatch.change_redshift.emit(redshift=self._redshift_z)

    @specviz_dispatch.register_listener("change_redshift")
    def change_redshift(self, redshift):
        """
        Change the redshift based on a message from specviz.

        :paramter: redshift - the Z value.
        :return: nothing
        """
        if self._redshift_z == redshift:
            # If the input redshift is the current value we have
            # then we are not going to do anything.
            return
        else:
            # This calls the setter above, so really, the magic is there.
            self.redshift_z = redshift

    def on_combobox_change(self, new_unit_name):
        """
        Callback for change in unitcombobox value
        :param event:
        :return:
        """
        # Get the new unit name from the selected value in the comboBox and
        # set that as the new unit that wavelengths will be converted to
        # new_unit_name = self._wavelength_combobox.currentText()
        self._new_units = self._units[self._units_titles.index(new_unit_name)]

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

    def get_new_units(self):
        return self._new_units


def _add_unit_to_list(unit_list, target_unit):

    if isinstance(target_unit, str):
        current_unit = u.Unit(target_unit)
        string_unit = target_unit
    else:
        current_unit = target_unit
        string_unit = target_unit.to_string()

    duplicate = False
    for unit in unit_list:
        if isinstance(unit, str):
            unit = u.Unit(unit)
        if unit == current_unit:
            duplicate = True
            break
    if not duplicate:
        unit_list.append(string_unit)
    return unit_list


def find_unit_index(unit_list, target_unit):
    if isinstance(target_unit, str):
        target_unit = u.Unit(target_unit)

    for i, unit in enumerate(unit_list):
        if isinstance(unit, str):
            unit = u.Unit(unit)
        if unit == target_unit:
            return i
    return None


def _get_power(numeric):
    if float(np.log10(numeric)).is_integer():
        power = int(np.log10(numeric))
    else:
        power = 0
    return power


class FluxUnitRegistry:
    def __init__(self):
        self._model_unit = u.Jy
        self.runtime_defined_units = []

    @staticmethod
    def _locally_defined_units():
        units = ['Jy', 'mJy', 'uJy',
                 'W / (m2 Hz)',
                 'eV / (s m2 Hz)',
                 'erg / (s cm2)',
                 'erg / (s cm2 um)',
                 'erg / (s cm2 Angstrom)',
                 'erg / (s cm2 Hz)',
                 'ph / (s cm2 um)',
                 'ph / (s cm2 Angstrom)',
                 'ph / (s cm2 Hz)']
        return units

    def is_compatible(self, unit):
        try:
            self._model_unit.to(unit, equivalencies=u.spectral_density(3500 * u.AA))
            return True
        except u.UnitConversionError:
            return False

    def get_unit_list(self, current_unit=None):
        unit_list = []
        item_list = []
        unit_list.extend(self._locally_defined_units())
        item_list.extend(self.runtime_defined_units)

        for item in item_list:
            unit_list = _add_unit_to_list(unit_list, item)

        if current_unit is not None:
            if isinstance(current_unit, str):
                current_unit = u.Unit(current_unit)
            unit_list = _add_unit_to_list(unit_list, current_unit)
        return unit_list

    def add_unit(self, item):
        if isinstance(item, str) \
                or isinstance(item, u.UnitBase):
            if item not in self.runtime_defined_units:
                self.runtime_defined_units.append(item)


class AreaUnitRegistry:
    def __init__(self):
        self._model_unit = [u.pixel, u.steradian]
        self.runtime_solid_angle_units = []
        self.runtime_pixel_units = []

    def is_compatible(self, unit):
        compatible = False
        for model_unit in self._model_unit:
            try:
                model_unit.to(unit)
                compatible = True
            except u.UnitConversionError:
                continue
        return compatible

    @staticmethod
    def _locally_defined_solid_angle_units():
        units = ["deg2",
                 "arcmin2",
                 "arcsec2",
                 'steradian',
                 "rad2"]

        return units

    @staticmethod
    def _locally_defined_pixel_units():
        units = ["pixel"]

        spaxel = u.def_unit('spaxel', u.astrophys.pix)
        u.add_enabled_units(spaxel)
        units.append('spaxel')

        return units

    def get_unit_list(self, pixel_only=False,
                      solid_angle_only=False,
                      current_unit=None):
        unit_list = []
        item_list = []
        if not solid_angle_only:
            unit_list.extend(self._locally_defined_pixel_units())
            item_list.extend(self.runtime_pixel_units)
        if not pixel_only:
            unit_list.extend(self._locally_defined_solid_angle_units())
            item_list.extend(self.runtime_solid_angle_units)

        for item in item_list:
            unit_list = _add_unit_to_list(unit_list, item)

        if current_unit is not None:
            if isinstance(current_unit, str):
                current_unit = u.Unit(current_unit)
            unit_list = _add_unit_to_list(unit_list, current_unit)
        return unit_list

    def add_pixel_unit(self, item):
        if isinstance(item, str) \
                or isinstance(item, u.UnitBase):
            if item not in self.runtime_pixel_units:
                self.runtime_pixel_units.append(item)

    def add_solid_angle_unit(self, item):
        if isinstance(item, str) \
                or isinstance(item, u.UnitBase):
            if item not in self.runtime_solid_angle_units:
                self.runtime_solid_angle_units.append(item)

    def add_unit(self, item):
        if isinstance(item, str):
            new_unit = u.unit(item)
        else:
            new_unit = item

        if new_unit.decompose() == u.pix.decompose():
            self.add_pixel_unit(new_unit)
        if 'solid angle' in new_unit.physical_type:
            self.add_solid_angle_unit(new_unit)


FLUX_UNIT_REGISTRY = FluxUnitRegistry()
AREA_UNIT_REGISTRY = AreaUnitRegistry()


class CubeVizUnit:
    def __init__(self, unit=None, unit_string=""):
        self._original_unit = unit
        self._original_unit_string = unit_string
        self._unit = unit
        self._unit_string = unit_string
        self._type = "CubeVizUnit"
        self.is_convertible = False

        self.message_box = None

    @property
    def unit(self):
        return self._unit

    @property
    def unit_string(self):
        return self._unit_string

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type):
        if isinstance(type, str):
            self._type = type

    def get_units(self):
        return self.unit_string

    def convert_from_original_unit(self, value, **kwargs):
        if not isinstance(value, int) and \
                not isinstance(value, float):
            raise ValueError("Expected float or int, got {} instead.".format(type(value)))

        if self.unit is None:
            return value

        new_value = value
        new_value *= self._original_unit.to(self._unit)

        if isinstance(new_value, u.Quantity):
            new_value = new_value.value

        return new_value

    def change_units(self):
        return True

    def reset_widgets(self):
        self.message_box = None
        return

    def populate_unit_layout(self, unit_layout, gui=None):

        if self.unit_string:
            default_message = "CubeViz can not convert this unit: {0}."
            default_message = default_message.format(self.unit_string)
        else:
            default_message = "Unit not found."

        default_label = QLabel(default_message)
        unit_layout.addWidget(default_label)
        return unit_layout

    def set_message_box(self, message_box):
        self.message_box = message_box
        self.message_box.setText("")


class SpectralFluxDensity(CubeVizUnit):
    def __init__(self, unit, unit_string,
                 power=None,
                 spectral_flux_density=None,
                 area=None,
                 is_formatted=False):
        super(SpectralFluxDensity, self).__init__(unit, unit_string)

        self._type = "FormattedSpectralFluxDensity" if is_formatted else "SpectralFluxDensity"
        self.is_convertible = True

        self.power = power
        self.spectral_flux_density = spectral_flux_density
        self.area = area

        self._original_power = power
        self._original_spectral_flux_density = spectral_flux_density
        self._original_area = area

        self.has_area = True if area is not None else False

        self.power_input = None
        self.flux_combo = None
        self.area_combo = None

        self.wave = 656.3 * u.nm

        FLUX_UNIT_REGISTRY.add_unit(spectral_flux_density)

    def convert_from_original_unit(self, value, wave=None, **kwargs):
        if self.unit is None and wave is None:
            return value

        new_value = value

        new_value *= 10**(self._original_power - self.power)
        new_value *= self._original_spectral_flux_density.to(self.spectral_flux_density,
                                                             equivalencies=u.spectral_density(wave))
        if self.has_area:
            new_value /= self._original_area.to(self.area)

        if isinstance(new_value, u.Quantity):
            new_value = new_value.value

        return new_value

    def reset_widgets(self):
        self.message_box = None
        self.power_input = None
        self.flux_combo = None
        self.area_combo = None

    def _get_current_power(self):
        if self.power is not None:
            power = self.power
        else:
            power = 0
        return power

    def _validate_input(self):
        red = "background-color: rgba(255, 0, 0, 128);"
        success = True
        if self.power_input is None \
                or self.flux_combo is None:
            success = False
            return success

        if self.area_combo is None and self.has_area:
            success = False
            return success

        # Check 1: power_input
        if self.power_input == "":
            self.power_input.setStyleSheet(red)
            success = False
        else:
            try:
                power = int(self.power_input.text())
                self.power_input.setStyleSheet("")
            except ValueError:
                self.power_input.setStyleSheet(red)
                success = False
        return success

    def change_units(self):
        success = self._validate_input()
        if not success:
            return success

        self.power = int(self.power_input.text())

        flux_string = self.flux_combo.currentText()
        flux_unit = u.Unit(flux_string)
        self.spectral_flux_density = flux_unit

        if self.has_area:
            area_string = self.area_combo.currentText()
            area_unit = u.Unit(area_string)
            self.area = area_unit
            unit_base = self.spectral_flux_density / self.area
        else:
            unit_base = self.spectral_flux_density

        self._unit = u.Unit((10**self.power) * unit_base)
        self._unit_string = self._unit.to_string()

        return success

    def _update_message(self):
        if self.message_box is None:
            return
        success = self._validate_input()
        if not success:
            self.message_box.setText("Error")
            return

        new_value = 1.0
        wave = self.wave

        power = int(self.power_input.text())
        new_value *= 10**(self._original_power - power)

        flux_string = self.flux_combo.currentText()
        flux_unit = u.Unit(flux_string)
        spectral_flux_density = flux_unit
        new_value *= self._original_spectral_flux_density.to(spectral_flux_density,
                                                             equivalencies=u.spectral_density(wave))

        if self.has_area:
            area_string = self.area_combo.currentText()
            area = u.Unit(area_string)
            new_value /= self._original_area.to(area)
            unit_base = spectral_flux_density / area
        else:
            unit_base = spectral_flux_density

        unit_base = u.Unit((10**power) * unit_base)

        if isinstance(new_value, u.Quantity):
            new_value = new_value.value

        if isinstance(unit_base, u.Quantity):
            unit_base = u.Unit(unit_base)

        message_param = (wave, self.unit.to_string(), new_value, unit_base)
        if 0.01 <= abs(new_value) <= 1000:
            message = "Data Unit: [{1}]\n" \
                      "New Unit: [{3}]\n" \
                      "1.0 [Data Unit] = {2:.2f} [New Unit]\n" \
                      "(at lambda = {0:0.4e})".format(*message_param)
        else:
            message = "Data Unit: [{1}]\n" \
                      "New Unit: [{3}]\n" \
                      "1.0 [Data Unit] = {2:0.2e} [New Unit]\n" \
                      "(at lambda = {0:0.4e})".format(*message_param)
        self.message_box.setText(message)

    def _on_flux_combo_change(self, index):
        current_string = self.flux_combo.currentText()
        flux_unit_str = self.spectral_flux_density.to_string()
        if current_string != flux_unit_str:
            self.power_input.setText("0")
        else:
            power = self._get_current_power()
            self.power_input.setText(str(power))

    def populate_unit_layout(self, unit_layout, gui=None):
        power = self._get_current_power()

        unit_layout.addWidget(QLabel("10^"))
        power_input = QLineEdit(str(power))
        power_input.setFixedWidth(30)
        self.power_input = power_input
        power_input.textChanged.connect(self._update_message)
        unit_layout.addWidget(power_input)

        unit_layout.addWidget(QLabel("   X   "))

        flux_unit_str = self.spectral_flux_density.to_string()
        flux_options = FLUX_UNIT_REGISTRY.get_unit_list(current_unit=flux_unit_str)
        index = find_unit_index(flux_options, flux_unit_str)
        if index is None:
            flux_options.append(flux_unit_str)
            index = flux_options.index(flux_unit_str)
        flux_combo = QComboBox()
        flux_combo.addItems(flux_options)
        flux_combo.setCurrentIndex(index)
        flux_combo.currentIndexChanged.connect(self._on_flux_combo_change)
        flux_combo.currentIndexChanged.connect(self._update_message)
        self.flux_combo = flux_combo
        unit_layout.addWidget(flux_combo)

        if self.area is not None:
            division = QLabel("   /   ")
            unit_layout.addWidget(division)

            area_str = self.area.to_string()
            area_options = AREA_UNIT_REGISTRY.get_unit_list()
            index = find_unit_index(area_options, area_str)
            if index is None:
                area_options.append(area_str)
                index = area_options.index(area_str)
            area_combo = QComboBox()
            area_combo.width()
            area_combo.addItems(area_options)
            area_combo.setCurrentIndex(index)
            area_combo.currentIndexChanged.connect(self._update_message)
            self.area_combo = area_combo
            unit_layout.addWidget(area_combo)
        unit_layout.addStretch(1)
        unit_layout.setSpacing(0)

        if self.message_box is not None:
            self._update_message()

        if gui is not None:
            cubeviz_layout = gui.cubeviz_layout
            if cubeviz_layout is not None:
                self.wave = cubeviz_layout.get_wavelength()
        return unit_layout


class UnknownUnit(CubeVizUnit):
    def __init__(self, unit, unit_string):
        super(UnknownUnit, self).__init__(unit, unit_string)
        self._type = "UnknownUnit"

        if unit is not None:
            self.is_convertible = True

        self.options_combo = None

    def change_units(self):
        if not self.is_convertible:
            return

        new_unit_string = self.options_combo.currentText()

        self._unit_string = new_unit_string
        self._unit = u.Unit(new_unit_string)

        return True

    def reset_widgets(self):
        self.message_box = None
        self.options_combo = None

    def _update_message(self):
        if self.message_box is None:
            return

        if not self.is_convertible:
            self.message_box.setText("")

        new_value = 1.0

        new_unit_string = self.options_combo.currentText()
        new_unit = u.Unit(new_unit_string)

        new_value *= self._original_unit.to(new_unit)

        if isinstance(new_value, u.Quantity):
            new_value = new_value.value

        message_param = (self._original_unit, new_unit_string, new_value)

        if 0.01 <= abs(new_value) <= 1000:
            message = "Data Units: [{0}]\n" \
                      "New Units: [{1}]\n" \
                      "1.0 [Data Unit] = {2:.2f} [New Unit]".format(*message_param)
        else:
            message = "Data Units: [{0}]\n" \
                      "New Units: [{1}]\n" \
                      "1.0 [Data Unit] = {2:0.2e} [New Unit]".format(*message_param)
        self.message_box.setText(message)

    def populate_unit_layout(self, unit_layout, gui=None):

        if self.unit is None:
            default_message = "CubeViz can not convert this unit: {0}."
            default_message = default_message.format(self.unit_string)
            default_label = QLabel(default_message)
            unit_layout.addWidget(default_label)
            return unit_layout
        unit_str = self.unit.to_string()
        options = self.unit.find_equivalent_units()
        options = [i.to_string() for i in options]
        if unit_str not in options:
            options.append(unit_str)
        index = options.index(unit_str)
        combo = QComboBox()
        # combo.setFixedWidth(200)
        combo.addItems(options)
        combo.setCurrentIndex(index)
        combo.currentIndexChanged.connect(self._update_message)
        self.options_combo = combo
        unit_layout.addWidget(combo)
        self._update_message()
        return unit_layout


class NoneUnit(CubeVizUnit):
    def __init__(self):
        super(NoneUnit, self).__init__(None, "")
        self._type = "NoneUnit"

    def populate_unit_layout(self, unit_layout, gui=None):
        default_message = "No Units."
        default_label = QLabel(default_message)
        unit_layout.addWidget(default_label)
        return unit_layout


class ConvertFluxUnitGUI(QDialog):
    def __init__(self, controller, parent=None):
        super(ConvertFluxUnitGUI, self).__init__(parent=parent)
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.title = "Unit Conversion"
        self.setMinimumSize(400, 200)

        self.cubeviz_layout = controller.cubeviz_layout

        self.controller = controller
        self.data = controller.data
        self.controller_components = controller._components

        self.current_unit = None

        self._init_ui()

    def _init_ui(self):
        # LINE 1: Data component drop down
        self.component_prompt = QLabel("Data Component:")
        self.component_prompt.setWordWrap(True)
        # Add the data component labels to the drop down, with the ComponentID
        # set as the userData:
        if self.parent is not None and hasattr(self.parent, 'data_components'):
            self.label_data = [(str(cid), cid) for cid in self.parent.data_components]
        else:
            self.label_data = [(str(cid), cid) for cid in self.data.visible_components]

        default_index = 0
        self.component_combo = QComboBox()
        self.component_combo.setFixedWidth(200)
        update_combobox(self.component_combo, self.label_data, default_index=default_index)
        self.component_combo.currentIndexChanged.connect(self.update_unit_layout)

        # hbl is short for Horizontal Box Layout
        hbl1 = QHBoxLayout()
        hbl1.addWidget(self.component_prompt)
        hbl1.addWidget(self.component_combo)
        hbl1.addStretch(1)

        # LINE 2: Unit conversion layout
        self.unit_layout = QHBoxLayout()  # this is hbl2

        # LINE 3: Unit conversion layout
        self.message_box = QLabel("")
        hbl3 = QHBoxLayout()
        hbl3.addWidget(self.message_box)
        hbl3.addStretch(1)

        # Line 4: Buttons
        self.okButton = QPushButton("Convert Units")
        self.okButton.clicked.connect(self.call_main)
        self.okButton.setDefault(True)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel)

        hbl4 = QHBoxLayout()
        hbl4.addStretch(1)
        hbl4.addWidget(self.cancelButton)
        hbl4.addWidget(self.okButton)

        vbl = QVBoxLayout()
        vbl.addLayout(hbl1)
        vbl.addLayout(self.unit_layout)
        vbl.addLayout(hbl3)
        vbl.addLayout(hbl4)
        self.setLayout(vbl)
        self.vbl = vbl

        self.update_unit_layout(default_index)

        self.show()

    def update_unit_layout(self, index):
        component_id = str(self.component_combo.currentData())

        widgets = (self.unit_layout.itemAt(i) for i in range(self.unit_layout.count()))
        for w in widgets:
            if isinstance(w, QSpacerItem):
                self.unit_layout.removeItem(w)
                continue
            elif isinstance(w, QWidgetItem):
                w = w.widget()

            if hasattr(w, "deleteLater"):
                w.deleteLater()

        self.message_box.setText("")

        if self.current_unit:
            self.current_unit.reset_widgets()

        if component_id in self.controller_components:
            cubeviz_unit = self.controller_components[component_id]
            self.current_unit = cubeviz_unit
            cubeviz_unit.set_message_box(self.message_box)
            cubeviz_unit.populate_unit_layout(self.unit_layout, self)
            if cubeviz_unit.is_convertible:
                self.okButton.setEnabled(True)
            else:
                self.okButton.setEnabled(False)
        else:
            self.current_unit = None
            default_message = "CubeViz can not convert this unit."
            default_label = QLabel(default_message)
            self.unit_layout.addWidget(default_label)
            self.okButton.setEnabled(False)

        self.unit_layout.update()
        self.vbl.update()

    def call_main(self):
        success = self.current_unit.change_units()
        if not success:
            # Todo: Warning should pop up
            return

        component_id = self.component_combo.currentData()
        self.data.get_component(component_id).units = self.current_unit.unit_string
        if self.cubeviz_layout is not None:
            self.cubeviz_layout.refresh_units(component_id)
        self.close()

    def cancel(self):
        self.close()


class FluxUnitController:
    def __init__(self, cubeviz_layout=None):
        self.cubeviz_layout = cubeviz_layout

        with open(DEFAULT_FLUX_UNITS_CONFIGS, 'r') as yamlfile:
            cfg = yaml.load(yamlfile)

        for new_unit_key in cfg["new_units"]:
            new_unit = cfg["new_units"][new_unit_key]
            try:
                u.Unit(new_unit["name"])
            except ValueError:
                if "base" in new_unit:
                    new_astropy_unit = u.def_unit(new_unit["name"], u.Unit(new_unit["base"]))
                else:
                    new_astropy_unit = u.def_unit(new_unit["name"])
            self.register_new_unit(new_astropy_unit)

        self._define_new_physical_types()

        self.registered_units = cfg["registered_units"]

        self.data = None
        self._components = {}

    @property
    def components(self):
        return self._components

    @staticmethod
    def register_new_unit(new_unit):
        u.add_enabled_units(new_unit)
        if FLUX_UNIT_REGISTRY.is_compatible(new_unit):
            FLUX_UNIT_REGISTRY.add_unit(new_unit)
        if new_unit.decompose() == u.pix.decompose() or \
                'solid angle' in new_unit.physical_type:
            AREA_UNIT_REGISTRY.add_unit(new_unit)

    @staticmethod
    def _define_new_physical_types():
        new_physical_types = [
            [(u.Jy / u.degree ** 2), 'SFD_over_solid_angle'],
            [(u.Jy / u.pix), 'SFD_over_pix']
        ]
        for model_unit, name in new_physical_types:
            try:
                u.def_physical_type(model_unit, name)
            except ValueError:
                continue

    @staticmethod
    def _sfd_over_solid_angle_to_cubeviz(unit, unit_string):
        power = _get_power(unit.scale)
        unit_list = unit.bases
        power_list = unit.powers

        index = None
        sfd_unit = None
        for i, un in enumerate(unit_list):
            if 'solid angle' == un.physical_type or \
                    'angle' == un.physical_type:
                index = i
            else:
                if sfd_unit is None:
                    sfd_unit = un ** power_list[i]
                else:
                    sfd_unit *= un ** power_list[i]

        if index is not None:
            angle_unit = unit_list[index] ** abs(power_list[index])
            if power == 0:
                sfd_unit = u.Unit(unit.scale * sfd_unit)

            cubeviz_unit = SpectralFluxDensity(unit, unit_string,
                                               power, sfd_unit, angle_unit)
        else:
            cubeviz_unit = UnknownUnit(unit, unit_string)
        return cubeviz_unit

    @staticmethod
    def _sfd_over_pix_to_cubeviz(unit, unit_string):
        power = _get_power(unit.scale)
        unit_list = unit.bases
        power_list = unit.powers

        index = None
        sfd_unit = None
        for i, un in enumerate(unit_list):
            if un.decompose() == u.pix.decompose():
                index = i
            else:
                if sfd_unit is None:
                    sfd_unit = un ** power_list[i]
                else:
                    sfd_unit *= un ** power_list[i]

        if index is not None:
            pix_unit = unit_list[index] ** abs(power_list[index])
            if power == 0:
                sfd_unit = u.Unit(unit.scale * sfd_unit)
            cubeviz_unit = SpectralFluxDensity(unit, unit_string,
                                               power, sfd_unit, pix_unit)
        else:
            cubeviz_unit = UnknownUnit(unit, unit_string)
        return cubeviz_unit

    @staticmethod
    def string_to_unit(unit_string):
        try:
            if unit_string:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', AstropyWarning)
                    astropy_unit = u.Unit(unit_string)
                return astropy_unit
        except ValueError:
            print("Warning: Failed to convert {0} to an astropy unit.".format(unit_string))
        return None

    @staticmethod
    def unit_to_string(unit):
        if unit is None:
            return ""
        elif isinstance(unit, str):
            return unit
        elif isinstance(unit, u.Unit):
            return unit.to_string()
        elif isinstance(unit, u.quantity.Quantity):
            return unit.unit.to_string()
        else:
            raise ValueError("Invalid input unit type {0}.".format(type(unit)))

    def add_component_unit(self, component_id, unit=None):
        component_id = str(component_id)
        unit_string = self.unit_to_string(unit)

        if not unit_string:
            cubeviz_unit = NoneUnit()
        elif unit_string in self.registered_units:
            registered_unit = self.registered_units[unit_string]
            if "astropy_unit_string" in registered_unit:
                unit_string = registered_unit["astropy_unit_string"]
            astropy_unit = self.string_to_unit(unit_string)
            spectral_flux_density = self.string_to_unit(registered_unit["spectral_flux_density"])
            if "area" in registered_unit:
                area = self.string_to_unit(registered_unit["area"])
            else:
                area = None

            numeric = spectral_flux_density.scale
            power = _get_power(numeric)
            if power != 0:
                spectral_flux_density /= u.Unit(numeric)
            cubeviz_unit = SpectralFluxDensity(astropy_unit, unit_string,
                                               power, spectral_flux_density, area,
                                               is_formatted=True)
        else:
            astropy_unit = self.string_to_unit(unit_string)
            if astropy_unit is None:
                cubeviz_unit = UnknownUnit(astropy_unit, unit_string)
            elif 'SFD_over_solid_angle' in astropy_unit.physical_type:
                cubeviz_unit = self._sfd_over_solid_angle_to_cubeviz(astropy_unit, unit_string)
            elif 'SFD_over_pix' in astropy_unit.physical_type:
                cubeviz_unit = self._sfd_over_pix_to_cubeviz(astropy_unit, unit_string)
            elif 'spectral flux density' in astropy_unit.physical_type:
                spectral_flux_density = astropy_unit
                numeric = spectral_flux_density.scale
                power = _get_power(numeric)
                if power != 0:
                    spectral_flux_density /= u.Unit(numeric)
                cubeviz_unit = SpectralFluxDensity(astropy_unit, unit_string,
                                                   power, spectral_flux_density,
                                                   area=None)
            else:
                cubeviz_unit = UnknownUnit(astropy_unit, unit_string)

        self._components[component_id] = cubeviz_unit
        return cubeviz_unit

    def remove_component_unit(self, component_id):
        component_id = str(component_id)
        if component_id in self._components:
            del self._components[component_id]

    def get_component_unit(self, component_id, cubeviz_unit=False):
        component_id = str(component_id)
        if component_id in self._components:
            if cubeviz_unit:
                return self._components[component_id]
            else:
                return self._components[component_id].unit
        return None

    def set_data(self, data):
        self.data = data
        self._components = {}
        for comp in data.visible_components:
            self.add_component_unit(comp, data.get_component(comp).units)

    def converter(self, parent=None):
        ex = ConvertFluxUnitGUI(self, parent)
