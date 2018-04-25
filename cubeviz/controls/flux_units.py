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
from astropy.wcs.utils import proj_plane_pixel_area
from specviz.third_party.glue.data_viewer import dispatch as specviz_dispatch

from ..messages import FluxUnitsUpdateMessage

OBS_WAVELENGTH_TEXT = 'Obs Wavelength'
REST_WAVELENGTH_TEXT = 'Rest Wavelength'

DEFAULT_FLUX_UNITS_CONFIGS = os.path.join(os.path.dirname(__file__), 'registered_flux_units.yaml')


def _add_unit_to_list(unit_list, target_unit):
    """
    Given a list of units, add target units
    after checking for duplicates
    :param unit_list: list of units or string
    :param target_unit: unit or string
    :return: updated unit
    """

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
    """
    Given a list of units or strings, find
    index of unit.
    :param unit_list: list of units or string
    :param target_unit: unit or string
    :return: updated unit
    """
    if isinstance(target_unit, str):
        target_unit = u.Unit(target_unit)

    for i, unit in enumerate(unit_list):
        if isinstance(unit, str):
            unit = u.Unit(unit)
        if unit == target_unit:
            return i
    return None


def _get_power(numeric):
    """
    Given a number, get the power if
    the power is an int. Else Return 0
    :param numeric: float or int
    :return: power if int, 0.0 if power is float
    """
    if float(np.log10(numeric)).is_integer():
        power = int(np.log10(numeric))
    else:
        power = 0
    return power


class FluxUnitRegistry:
    """
    Saves a list of spectral flux density units.
    """
    def __init__(self):
        self._model_unit = u.Jy  # Will be used for compatibility checks
        self.runtime_defined_units = []  # Stores list of runtime units

    @staticmethod
    def _locally_defined_units():
        """
        list of defined spectral flux density units.
        :return: list of unit strings
        """
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
        """
        Check if unit can be converted to units
        in this registry. Uses model unit to check.
        :param unit: Unit or unit str
        :return: bool
        """
        try:
            self._model_unit.to(unit, equivalencies=u.spectral_density(3500 * u.AA))
            return True
        except u.UnitConversionError:
            return False

    def get_unit_list(self, current_unit=None):
        """
        Returns a list of unit strings in the registry.
        Adds current_unit if not duplicated. Registered
        units are added first.
        :param current_unit: Unit or unit str
        :return: list of unit str
        """
        unit_list = []  # final list
        item_list = []  # items to be checked if duplicated
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
        """
        Add new unit
        :param item: unit or unit str
        """
        if isinstance(item, str) \
                or isinstance(item, u.UnitBase):
            if item not in self.runtime_defined_units:
                self.runtime_defined_units.append(item)


class AreaUnitRegistry:
    """
    Saves a list of area units.
    There are 2 kinds of area units:
    1. solid angles
    2. pixels
    These maybe interchangeable if wcs pixel_scale
    is available.
    """
    def __init__(self):
        self._model_unit = [u.pixel, u.steradian]  # Will be used for compatibility checks
        self.runtime_solid_angle_units = []  # Stores list of runtime angle units
        self.runtime_pixel_units = []  # Stores list of runtime pixel units

    @staticmethod
    def _locally_defined_solid_angle_units():
        """
        list of defined spectral solid angle units.
        :return: list of unit strings
        """
        units = ["deg2",
                 "arcmin2",
                 "arcsec2",
                 'steradian',
                 "rad2"]

        return units

    @staticmethod
    def _locally_defined_pixel_units():
        """
        list of defined spectral pixel units.
        :return: list of unit strings
        """
        units = ["pixel"]

        spaxel = u.def_unit('spaxel', u.astrophys.pix)
        u.add_enabled_units(spaxel)
        units.append('spaxel')

        return units

    def is_compatible(self, unit):
        """
        Check if unit can be converted to units
        in this registry. Uses model units to check.
        :param unit: Unit or unit str
        :return: bool
        """
        compatible = False
        for model_unit in self._model_unit:
            try:
                model_unit.to(unit)
                compatible = True
            except u.UnitConversionError:
                continue
        return compatible

    def get_unit_list(self, pixel_only=False,
                      solid_angle_only=False,
                      current_unit=None):
        """
        Returns a list of unit strings in the registry.
        Adds current_unit if not duplicated. Registered
        units are added first.
        :param pixel_only: (bool) Return pixel units only
        :param solid_angle_only: (bool) Return solid_angle_only units only
        :param current_unit: Unit or unit str
        :return: list of unit str
        """
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
        """
        Add new pixel unit
        :param item: unit or unit str
        """
        if isinstance(item, str) \
                or isinstance(item, u.UnitBase):
            if item not in self.runtime_pixel_units:
                self.runtime_pixel_units.append(item)

    def add_solid_angle_unit(self, item):
        """
        Add new solid angle unit
        :param item: unit or unit str
        """
        if isinstance(item, str) \
                or isinstance(item, u.UnitBase):
            if item not in self.runtime_solid_angle_units:
                self.runtime_solid_angle_units.append(item)

    def add_unit(self, item):
        """
        Check for type and add new unit
        :param item: unit or unit str
        """
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
    """
    Unit container with the following functions:
        - Stores units and names
        - Converts units
        - Updates units
        - Populates conversion gui with widgets custom to
          the stored unit type

    Types of CubeVizUnit:
        - CubeVizUnit (base class)
        - SpectralFluxDensity
            - FormattedSpectralFluxDensity
            - SpectralFluxDensity
        - UnknownUnit
        - NoneUnit
    """
    def __init__(self, unit=None, unit_string=""):
        """
        :param unit: astropy unit or None
        :param unit_string: Unit as a string
        """
        self._controller = None  # Unit controller (property)
        self._original_unit = unit  # the data's actual units
        self._original_unit_string = unit_string  # original_unit as str
        self._unit = unit  # Current Unit
        self._unit_string = unit_string  # unit as str
        self._type = "CubeVizUnit"  # Type of CubeVizUnit
        self.is_convertible = False  # If unit is convertible

        self.message_box = None  # Pointer to gui message box

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

    @property
    def controller(self):
        return self._controller

    @controller.setter
    def controller(self, controller):
        self._controller = controller

    def get_units(self):
        return self.unit_string

    def convert_from_original_unit(self, value, **kwargs):
        """
        Given a value from the data, convert it to current
        units.
        :param value: float
        :param kwargs:
        :return: converted value
        """
        if not isinstance(value, int) \
                and not isinstance(value, float) \
                and not isinstance(value, np.ndarray):
            raise ValueError("Expected float or int, got {} instead.".format(type(value)))

        if self.unit is None:
            return value

        new_value = value
        new_value *= self._original_unit.to(self._unit)

        if isinstance(new_value, u.Quantity):
            new_value = new_value.value

        return new_value

    def change_units(self):
        """
        This function is called when accept is pressed on the
        unit conversion gui
        :return: (bool) True if unit update is successful
        """
        return True

    def reset_widgets(self):
        """
        Reset all attributes pointing to widgets in the
        conversion gui
        """
        self.message_box = None
        return

    def populate_unit_layout(self, unit_layout, gui=None):
        """
        Populate horizontal layout (living on conversion gui)
        with appropriate widgets.
        :param unit_layout: (QHBoxLayout) Horizontal layout
        :param gui: conversion gui
        :return: updated unit_layout
        """

        if self.unit_string:
            default_message = "CubeViz can not convert this unit: {0}."
            default_message = default_message.format(self.unit_string)
        else:
            default_message = "Unit not found."

        default_label = QLabel(default_message)
        unit_layout.addWidget(default_label)
        return unit_layout

    def set_message_box(self, message_box):
        """
        Sets local attribute to message box on
        the onversion gui.
        :param message_box: QLabel
        """
        self.message_box = message_box
        self.message_box.setText("")


class SpectralFluxDensity(CubeVizUnit):
    """
    CubeVizUnit for spectral flux density.
    See CubeVizUnit for more info.
    SpectralFluxDensity breaks the units into:
        - power
        - spectral_flux_density
        - area
    These units are recombined as follows:

        unit = (10 ** power) * spectral_flux_density / area

    """
    def __init__(self, unit, unit_string,
                 power=None,
                 spectral_flux_density=None,
                 area=None,
                 is_formatted=False):
        """
        :param unit: astropy unit
        :param unit_string: unit as string
        :param power: power of scalar multiplier if multiplier is 10^X
        :param spectral_flux_density: astropy unit of spectral flux density
        :param area: astropy unit area
        :param is_formatted: True if unit is in registered yaml file
        """
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

        self.wave = 656.3 * u.nm  # Used for conversion preview. Updated latter.

        # Add unit to FLUX_UNIT_REGISTRY. (not added if duplicate)
        FLUX_UNIT_REGISTRY.add_unit(spectral_flux_density)

    def convert_from_original_unit(self, value, wave=None, **kwargs):
        """
        Given a value from the data, convert it to current
        units.
        :param value: float
        :param wave: float: wavelength
        :param kwargs:
        :return: converted value
        """
        if self.unit is None and wave is None:
            return value

        new_value = value

        new_value *= 10**(self._original_power - self.power)
        new_value *= self._original_spectral_flux_density.to(self.spectral_flux_density,
                                                             equivalencies=u.spectral_density(wave))
        if self.has_area:
            pixel_area = self.controller.pixel_area

            if self.area.decompose() == u.pix.decompose() \
                    and 'solid angle' in self._original_area.physical_type:
                area = u.Unit((self._original_area / pixel_area).decompose())
                new_value /= area.to(self.area)
            elif 'solid angle' in self.area.physical_type \
                    and self._original_area.decompose() == u.pix.decompose():
                area = u.Unit((self._original_area * pixel_area).decompose())
                new_value /= area.to(self.area)
            else:
                new_value /= self._original_area.to(self.area)

        if isinstance(new_value, u.Quantity):
            new_value = new_value.value

        return new_value

    def reset_widgets(self):
        """
        This function is called when accept is pressed on the
        unit conversion gui
        :return: (bool) True if unit update is successful
        """
        self.message_box = None
        self.power_input = None
        self.flux_combo = None
        self.area_combo = None

    def _get_current_power(self):
        """
        :return: current power, 0 if none
        """
        if self.power is not None:
            power = self.power
        else:
            power = 0
        return power

    def _validate_input(self):
        """
        Validate user input from converter gui.
        :return: bool: True if input is valid
        """
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
        """
        This function is called when accept is pressed on the
        unit conversion gui
        :return: (bool) True if unit update is successful
        """

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
        """
        Callback for when options in conversion gui change. Message
        is set to info about the units a preview of the conversion.
        """
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

        pixel_area = None
        if self.has_area:
            area_string = self.area_combo.currentText()
            area = u.Unit(area_string)
            pixel_area = self.controller.pixel_area
            if area.decompose() == u.pix.decompose() \
                    and 'solid angle' in self._original_area.physical_type:
                temp_area = (self._original_area / pixel_area).decompose()
                new_value /= temp_area.to(area)
            elif 'solid angle' in area.physical_type \
                    and self._original_area.decompose() == u.pix.decompose():
                temp_area = (self._original_area * pixel_area).decompose()
                new_value /= temp_area.to(area)
            else:
                new_value /= self._original_area.to(area)
            unit_base = spectral_flux_density / area
        else:
            unit_base = spectral_flux_density

        unit_base = u.Unit((10**power) * unit_base)

        if isinstance(new_value, u.Quantity):
            new_value = new_value.value

        if isinstance(unit_base, u.Quantity):
            unit_base = u.Unit(unit_base)

        if pixel_area is None:
            message_param = (wave, self._original_unit.to_string(), new_value, unit_base)
            if 0.01 <= abs(new_value) <= 1000:
                message = "Original Units: [{1}]\n\n" \
                          "New Units: [{3}]\n\n" \
                          "1.0 [Original Units] = {2:.2f} [New Units]\n" \
                          "(at lambda = {0:0.4e})".format(*message_param)
            else:
                message = "Original Units: [{1}]\n\n" \
                          "New Units: [{3}]\n\n" \
                          "1.0 [Original Units] = {2:0.2e} [New Units]\n" \
                          "(at lambda = {0:0.4e})".format(*message_param)
        else:
            try:
                pixel_area = pixel_area.to("arcsec2 / pix")
                if isinstance(pixel_area, float):
                    pixel_area = pixel_area * u.arcsec ** 2 / u.pixel
            except (ValueError, u.UnitConversionError):
                pass
            message_param = (wave, self._original_unit.to_string(), new_value, unit_base, pixel_area)
            if 0.01 <= abs(new_value) <= 1000:
                message = "Original Units: [{1}]\n\n" \
                          "New Units: [{3}]\n\n" \
                          "Pixel Area (Scale): {4:.2e}\n\n" \
                          "1.0 [Original Units] = {2:.2f} [New Units]\n" \
                          "(at lambda = {0:0.4e})".format(*message_param)
            else:
                message = "Original Units: [{1}]\n\n" \
                          "New Units: [{3}]\n\n" \
                          "Pixel Area (Scale): {4:.2e}\n\n" \
                          "1.0 [Original Units] = {2:0.2e} [New Units]\n" \
                          "(at lambda = {0:0.4e})".format(*message_param)
        self.message_box.setText(message)

    def _on_flux_combo_change(self, index):
        """
        Callback for flux combo
        :param index:
        :return:
        """
        current_string = self.flux_combo.currentText()
        flux_unit_str = self.spectral_flux_density.to_string()
        if current_string != flux_unit_str:
            self.power_input.setText("0")
        else:
            power = self._get_current_power()
            self.power_input.setText(str(power))

    def populate_unit_layout(self, unit_layout, gui=None):
        """
        Populate horizontal layout (living on conversion gui)
        with appropriate widgets. Set wave attribute to current
        wavelength.

        Layouts:
            10^[QLineEdit] X [QComboBox] / [QComboBox]
                        or
            10^[QLineEdit] X [QComboBox]

        :param unit_layout: (QHBoxLayout) Horizontal layout
        :param gui: conversion gui
        :return: updated unit_layout
        """

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
        if flux_unit_str in flux_options:
            index = flux_options.index(flux_unit_str)
        else:
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
            if self.controller is None:
                no_pixel_area = True
            else:
                no_pixel_area = self.controller.pixel_area is None

            if self.area.decompose() == u.pix.decompose() and no_pixel_area:
                area_options = AREA_UNIT_REGISTRY.get_unit_list(pixel_only=True)
            elif 'solid angle' in self.area.physical_type and no_pixel_area:
                area_options = AREA_UNIT_REGISTRY.get_unit_list(solid_angle_only=True)
            else:
                area_options = AREA_UNIT_REGISTRY.get_unit_list()

            if area_str in area_options:
                index = area_options.index(area_str)
            else:
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
    """
    CubeVizUnit for any unit with a unit_string.
    Does not need to have an astropy unit.
    """
    def __init__(self, unit, unit_string):
        super(UnknownUnit, self).__init__(unit, unit_string)
        self._type = "UnknownUnit"

        if unit is not None:
            self.is_convertible = True

        self.options_combo = None

    def change_units(self):
        """
        This function is called when accept is pressed on the
        unit conversion gui
        :return: (bool) True if unit update is successful
        """
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
        """
        Callback for when options in conversion gui change. Message
        is set to info about the units a preview of the conversion.
        """
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
            message = "Original Units: [{0}]\n" \
                      "New Units: [{1}]\n" \
                      "1.0 [Original Units] = {2:.2f} [New Units]".format(*message_param)
        else:
            message = "Original Units: [{0}]\n" \
                      "New Units: [{1}]\n" \
                      "1.0 [Original Units] = {2:0.2e} [New Units]".format(*message_param)
        self.message_box.setText(message)

    def populate_unit_layout(self, unit_layout, gui=None):
        """
        Populate horizontal layout (living on conversion gui)
        with appropriate widgets.

        Layouts:
            [QComboBox]
               or
            default_message

        :param unit_layout: (QHBoxLayout) Horizontal layout
        :param gui: conversion gui
        :return: updated unit_layout
        """

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
    """
    CubeVizUnit for components with no
    units and unit strings
    """
    def __init__(self):
        super(NoneUnit, self).__init__(None, "")
        self._type = "NoneUnit"

    def populate_unit_layout(self, unit_layout, gui=None):
        """
        Populate horizontal layout (living on conversion gui)
        with appropriate widgets.

        Layouts:
            default_message

        :param unit_layout: (QHBoxLayout) Horizontal layout
        :param gui: conversion gui
        :return: updated unit_layout
        """
        default_message = "No Units."
        default_label = QLabel(default_message)
        unit_layout.addWidget(default_label)
        return unit_layout


class ConvertFluxUnitGUI(QDialog):
    """
    GUI for unit conversions
    """
    def __init__(self, controller, parent=None):
        super(ConvertFluxUnitGUI, self).__init__(parent=parent)
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.title = "Unit Conversion"
        self.setMinimumSize(400, 270)

        self.cubeviz_layout = controller.cubeviz_layout
        self._hub = self.cubeviz_layout.session.hub

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
        # This layout is filled by CubeVizUnit
        self.unit_layout = QHBoxLayout()  # this is hbl2

        # LINE 3: Message box
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
        """
        Call back for component selection drop down.
        """
        component_id = str(self.component_combo.currentData())

        # STEP1: Clean up widgets from last component
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

        # STEP2: Add now component and connect to CubeVizUnit
        #        so that new widgets are populated.
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
        """
        Calls CubeVizUnit.change_units to finalize
        conversions. Updates plots with new units.
        :return:
        """
        success = self.current_unit.change_units()
        if not success:
            # Todo: Warning should pop up
            return

        component_id = self.component_combo.currentData()
        self.data.get_component(component_id).units = self.current_unit.unit_string
        msg = FluxUnitsUpdateMessage(self, self.current_unit.unit, component_id)
        self._hub.broadcast(msg)
        self.close()

    def cancel(self):
        self.close()


class FluxUnitController:
    """
    Main controller for flux units.
    One FluxUnitController can only
    handle one glue data.
    """
    def __init__(self, cubeviz_layout=None):
        self.cubeviz_layout = cubeviz_layout

        # Load up configurations from yaml file
        with open(DEFAULT_FLUX_UNITS_CONFIGS, 'r') as yamlfile:
            cfg = yaml.load(yamlfile)

        # Define and add new units to astropy
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

        # Formatted units
        self.formatted_units = cfg["formatted_units"]

        self.data = None
        self.wcs = None
        self._components = {}

    @property
    def components(self):
        return self._components

    @property
    def pixel_area(self):
        if self.wcs is None:
            return None
        try:
            top_unit = u.Unit(self.wcs.wcs.cunit[0])
            pixel_area = proj_plane_pixel_area(self.wcs) * (top_unit ** 2) / u.pix
            u.spectral_density.pixel_area = pixel_area
            return pixel_area
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def register_new_unit(new_unit):
        """
        Add new unit to astropy.units
        :param new_unit: astropy unit
        """
        u.add_enabled_units(new_unit)
        if FLUX_UNIT_REGISTRY.is_compatible(new_unit):
            FLUX_UNIT_REGISTRY.add_unit(new_unit)
        if new_unit.decompose() == u.pix.decompose() or \
                'solid angle' in new_unit.physical_type:
            AREA_UNIT_REGISTRY.add_unit(new_unit)

    @staticmethod
    def _define_new_physical_types():
        """
        Two new types of units defined:
            - SFD_over_solid_angle = spectral_flux_density / (degree^2)
            - SFD_over_pix = spectral_flux_density / pixel
        """
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
        """
        Decompose sfd_over_solid_angle to CubeVizUnit
        NB: SFD_over_solid_angle = spectral_flux_density / (degree^2)
        :param unit: astropy unit
        :param unit_string: astropy unit
        :return: CubeVizUnit
        """
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
        """
        Decompose sfd_over_pix to CubeVizUnit
        NB: SFD_over_pix = spectral_flux_density / pixel
        :param unit: astropy unit
        :param unit_string: astropy unit
        :return: CubeVizUnit
        """
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
        """
        Unit str -> astropy unit
        :param unit_string: str
        :return: astropy unit. None otherwise
        """
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
        """
        astropy unit -> unit str
        :param unit: astropy unit
        :return: str
        """
        if unit is None:
            return ""
        elif isinstance(unit, str):
            return unit
        elif isinstance(unit, u.UnitBase):
            return unit.to_string()
        elif isinstance(unit, u.quantity.Quantity):
            return unit.unit.to_string()
        else:
            raise ValueError("Invalid input unit type {0}.".format(type(unit)))

    def add_component_unit(self, component_id, unit=None):
        """
        Add or update componet unit.
        :param component_id: component id or str
        :param unit: string or astropy unit
        :return: CubeVizUnit
        """
        component_id = str(component_id)
        unit_string = self.unit_to_string(unit)

        # IF: empty unit or no unit
        if not unit_string:
            cubeviz_unit = NoneUnit()
        # ELSE IF: formatted unit
        elif unit_string in self.formatted_units:
            registered_unit = self.formatted_units[unit_string]
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
            # IF: no astropy unit component
            if astropy_unit is None:
                cubeviz_unit = UnknownUnit(astropy_unit, unit_string)
            # ELSE IF: astropy unit type is spectral_flux_density / solid_angle
            elif 'SFD_over_solid_angle' in astropy_unit.physical_type:
                cubeviz_unit = self._sfd_over_solid_angle_to_cubeviz(astropy_unit, unit_string)
            # ELSE IF: astropy unit type is spectral_flux_density / pixel
            elif 'SFD_over_pix' in astropy_unit.physical_type:
                cubeviz_unit = self._sfd_over_pix_to_cubeviz(astropy_unit, unit_string)
            # ELSE IF: astropy unit type is spectral_flux_density
            elif 'spectral flux density' in astropy_unit.physical_type:
                spectral_flux_density = astropy_unit
                numeric = spectral_flux_density.scale
                power = _get_power(numeric)
                if power != 0:
                    spectral_flux_density /= u.Unit(numeric)
                cubeviz_unit = SpectralFluxDensity(astropy_unit, unit_string,
                                                   power, spectral_flux_density,
                                                   area=None)
            # ELSE: astropy unit type is not special
            else:
                cubeviz_unit = UnknownUnit(astropy_unit, unit_string)

        cubeviz_unit.controller = self
        self._components[component_id] = cubeviz_unit
        return cubeviz_unit

    def remove_component_unit(self, component_id):
        """
        Remove component from controller
        :param component_id: component id or str
        """
        component_id = str(component_id)
        if component_id in self._components:
            del self._components[component_id]

    def get_component_unit(self, component_id, cubeviz_unit=False):
        """
        Get component units
        :param component_id: component id or str
        :param cubeviz_unit: if True: return CubeVizUnit
                             else: return astropy unit
        :return: CubeVizUnit, astropy unit or None
        """
        component_id = str(component_id)
        if component_id in self._components:
            if cubeviz_unit:
                return self._components[component_id]
            else:
                return self._components[component_id].unit
        return None

    def set_data(self, data):
        """
        Add glue data and its components to controller.
        glue components' units attribute should contain a
        string with desired units for that component. This
        controller will use the string in that attribute
        to construct and assign units.
        :param data: glue data
        :return:
        """
        self.data = data
        self._components = {}
        for comp in data.visible_components:
            self.add_component_unit(comp, data.get_component(comp).units)

        wcs = data.coords.wcs
        if wcs is not None:
            self.wcs = wcs
        self.pixel_area

    def converter(self, parent=None):
        """
        Launch Converter GUI
        :param parent: application
        :return: ConvertFluxUnitGUI instance
        """
        ex = ConvertFluxUnitGUI(self, parent)
        return ex
