import numpy as np

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QDialog,  QPushButton, QLabel, QHBoxLayout, QVBoxLayout,
    QComboBox, QLineEdit, QWidgetItem, QSpacerItem, QMessageBox
)

from glue.utils.qt import update_combobox

from astropy import units as u
from astropy.units.quantity import Quantity

from ..messages import FluxUnitsUpdateMessage

from .flux_unit_registry import (FLUX_UNIT_REGISTRY, AREA_UNIT_REGISTRY, FORMATTED_UNITS,
                                 NONE_CubeVizUnit, UNKNOWN_CubeVizUnit, ASTROPY_CubeVizUnit,
                                 CUBEVIZ_UNIT_TYPES)


def find_unit_index(unit_list, target_unit):
    """
    Given a list of units or strings, find
    index of unit.
    :param unit_list: list of units or string
    :param target_unit: unit or string
    :return: unit index
    """

    # Make both a string and astropy version
    if not isinstance(target_unit, str):
        target_unit = u.Unit(target_unit).to_string()

    # Create list of all astropy Unit things
    temp_list = [unit.to_string() if not isinstance(unit, str)
                 else u.Unit(unit).to_string() for unit in unit_list]

    if target_unit in temp_list:
        return temp_list.index(target_unit)
    return None


def _get_power(numeric):
    """
    Given a number, get the power if
    the power is an int. Else Return 0
    :param numeric: float or int
    :return: power if int, 0.0 if power is float
    """
    exponent = float(np.log10(numeric))
    return int(exponent) if exponent.is_integer() else 0


class CubeVizUnitLayout:
    """
    This implements a specialized horizontal layout
    in the converter gui. This layout contains
    inputs specific to the unit type. This class
    is responsible for the following tasks:
        - Populate the UI horizontal layout
        - Contain user input widgets (QLineEdit etc..)
        - Set displayed messages on the UI
        - Get units from the user input
    """
    def __init__(self, cubeviz_unit):
        self.cubeviz_unit = cubeviz_unit

        self._unit = cubeviz_unit.unit
        self._unit_string = cubeviz_unit.unit_string

        self.message_box = None  # Pointer to gui message box

    def set_message_box(self, message_box):
        """
        Sets local attribute to message box on
        the onversion gui.
        :param message_box: QLabel
        """
        self.message_box = message_box
        self.message_box.setText("")

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

        if self.cubeviz_unit.unit_string:
            default_message = "CubeViz can not convert this unit: {0}."
            default_message = default_message.format(self.cubeviz_unit.unit_string)
        else:
            default_message = "No Units."

        default_label = QLabel(default_message)
        unit_layout.addWidget(default_label)
        return unit_layout

    @property
    def new_unit(self):
        return self._unit


class AstropyUnitLayout(CubeVizUnitLayout):
    """
    This implements a specialized horizontal layout
    in the converter gui. This layout contains
    inputs specific to the unit type. This class
    sets up the layout for regular astropy units.
    """
    def __init__(self, cubeviz_unit):
        super(AstropyUnitLayout, self).__init__(cubeviz_unit)

        self.options_combo = None

    def reset_widgets(self):
        self.message_box = None
        self.options_combo = None

    def change_units(self):
        """
        This function is called when accept is pressed on the
        unit conversion gui
        :return: (bool) True if unit update is successful
        """

        new_unit_string = self.options_combo.currentText()

        self._unit_string = new_unit_string
        self._unit = u.Unit(new_unit_string)
        return True

    def _update_message(self):
        """
        Callback for when options in conversion gui change. Message
        is set to info about the units a preview of the conversion.
        """
        if self.message_box is None:
            return

        new_unit_string = self.options_combo.currentText()
        new_unit = u.Unit(new_unit_string)

        new_value = self.cubeviz_unit.convert_value(1.0, new_unit=new_unit)

        message_param = (self.cubeviz_unit.original_unit.to_string(), new_unit_string, new_value)

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

        :param unit_layout: (QHBoxLayout) Horizontal layout
        :param gui: conversion gui
        :return: updated unit_layout
        """

        unit_str = self._unit.to_string()
        options = self._unit.find_equivalent_units(include_prefix_units=True)
        options = [i.to_string() for i in options]
        options.sort(key=lambda x: x.upper())
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


class SpectralFluxDensityLayout(CubeVizUnitLayout):
    """
    This implements a specialized horizontal layout
    in the converter gui. This layout contains
    inputs specific to the unit type. This class
    sets up the layout for regular astropy
    spectral flux density units.
    """
    def __init__(self,
                 cubeviz_unit,
                 power=None,
                 spectral_flux_density=None,
                 area=None,
                 wave=None,
                 pixel_area=None):

        super(SpectralFluxDensityLayout, self).__init__(cubeviz_unit)

        self.power = power
        self.spectral_flux_density = spectral_flux_density
        self.area = area

        self._original_unit = cubeviz_unit.original_unit

        self.has_area = True if area is not None else False

        self.power_input = None
        self.flux_combo = None
        self.area_combo = None

        if wave is not None:
            self.wave = wave
        else:
            self.wave = 656.3 * u.nm  # Used for conversion preview. Updated latter.

        self.pixel_area = pixel_area

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
        self.spectral_flux_density = u.Unit(flux_string)

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

        power = int(self.power_input.text())

        flux_string = self.flux_combo.currentText()
        spectral_flux_density = u.Unit(flux_string)

        if self.has_area:
            area_string = self.area_combo.currentText()
            area = u.Unit(area_string)
            unit_base = spectral_flux_density / area
        else:
            unit_base = spectral_flux_density

        unit_base = u.Unit((10**power) * unit_base)

        if isinstance(unit_base, Quantity):
            unit_base = u.Unit(unit_base)

        new_value = self.cubeviz_unit.convert_value(1.0,
                                                    wave=self.wave,
                                                    new_unit=unit_base)

        if self.pixel_area is not None:
            pixel_area = "{0:.2e}".format(self.pixel_area)
        else:
            pixel_area = "N/A"

        message_param = (self.cubeviz_unit.original_unit.to_string(),
                         unit_base,
                         pixel_area,
                         new_value,
                         self.wave)
        if 0.001 <= abs(new_value) <= 1000:
            message = "Original Units: [{0}]\n\n" \
                      "New Units: [{1}]\n\n" \
                      "Pixel Area (Scale): {2}\n\n" \
                      "1.000 [Original Units] = {3:.3f} [New Units]\n" \
                      "(at lambda = {4:0.4e})".format(*message_param)
        else:
            message = "Original Units: [{0}]\n\n" \
                      "New Units: [{1}]\n\n" \
                      "Pixel Area (Scale): {2}\n\n" \
                      "1.0 [Original Units] = {3:0.2e} [New Units]\n" \
                      "(at lambda = {4:0.4e})".format(*message_param)

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
        flux_options = FLUX_UNIT_REGISTRY.compose_unit_list(current_unit=flux_unit_str)
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

            no_pixel_area = self.pixel_area is None

            if self.area.decompose() == u.pix.decompose() and no_pixel_area:
                area_options = AREA_UNIT_REGISTRY.compose_unit_list(pixel_only=True)
            elif 'solid angle' in self.area.physical_type and no_pixel_area:
                area_options = AREA_UNIT_REGISTRY.compose_unit_list(solid_angle_only=True)
            else:
                area_options = AREA_UNIT_REGISTRY.compose_unit_list()

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

        return unit_layout


def decompose_sfd_over_solid_angle(unit):
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

        return [power, sfd_unit, angle_unit]
    else:
        return [None, unit, None]


def decompose_sfd_over_pix(unit):
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
        return [power, sfd_unit, pix_unit]
    else:
        return [None, unit, None]


def assign_cubeviz_unit_layout(cubeviz_unit, pixel_area=None, wave=None):
    """
    This is used to break down the unit and assign the
    appropriate conversion layout.
    Potential unit types are:
        - no units or not-astropy units -> CubeVizUnitLayout
        - regular astropy unit -> AstropyUnitLayout
        - spectral_flux_density -> SpectralFluxDensityLayout
        - spectral_flux_density / solid_angle -> SpectralFluxDensityLayout
        - spectral_flux_density / pixel -> SpectralFluxDensityLayout
    :param cubeviz_unit: CubeVizUnit
    :param pixel_area: Pixel area to use for conversion previews
    :param wave: Wavelength used for conversion previews
    :return:
    """

    if cubeviz_unit.type in [NONE_CubeVizUnit, UNKNOWN_CubeVizUnit]:
        layout = CubeVizUnitLayout(cubeviz_unit)
    else:
        astropy_unit = cubeviz_unit.unit
        # IF: astropy unit type is spectral_flux_density / solid_angle
        if astropy_unit.is_equivalent((u.Jy / u.degree ** 2),
                                      equivalencies=u.spectral_density.get_basic_relations(656.3*u.nm)):
            power, sfd_unit, area = decompose_sfd_over_solid_angle(astropy_unit)
            layout = SpectralFluxDensityLayout(cubeviz_unit, power, sfd_unit, area,
                                               wave, pixel_area)
        # ELSE IF: astropy unit type is spectral_flux_density / pixel
        elif astropy_unit.is_equivalent((u.Jy / u.pix),
                                        equivalencies=u.spectral_density.get_basic_relations(656.3*u.nm)):
            power, sfd_unit, area = decompose_sfd_over_pix(astropy_unit)
            layout = SpectralFluxDensityLayout(cubeviz_unit, power, sfd_unit, area,
                                               wave, pixel_area)
        # ELSE IF: astropy unit type is spectral_flux_density
        elif 'spectral flux density' in astropy_unit.physical_type:
            sfd_unit = astropy_unit
            numeric = sfd_unit.scale
            power = _get_power(numeric)
            layout = SpectralFluxDensityLayout(cubeviz_unit, power, sfd_unit, None,
                                               wave, pixel_area)
        # ELSE: astropy unit type is not special
        else:
            layout = AstropyUnitLayout(cubeviz_unit)

    return layout


class ConvertFluxUnitGUI(QDialog):
    """
    GUI for unit conversions
    """
    def __init__(self, controller, parent=None, convert_data=False):
        super(ConvertFluxUnitGUI, self).__init__(parent=parent)
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.title = "Unit Conversion"
        self.setMinimumSize(400, 270)

        self.convert_data = convert_data

        self.cubeviz_layout = controller.cubeviz_layout
        self._hub = self.cubeviz_layout.session.hub

        self.controller = controller
        self.data = controller.data
        self.controller_components = controller._components

        self.current_unit = None
        self.current_layout = None

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
        ok_text = "Convert Data" if self.convert_data else "Convert Displayed Units"
        ok_function = self.convert_data_units if self.convert_data else self.convert_displayed_units
        self.okButton = QPushButton(ok_text)
        self.okButton.clicked.connect(ok_function)
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
        component_id = self.component_combo.currentData()

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

        if self.current_layout:
            self.current_layout.reset_widgets()

        # STEP2: Add now component and connect to CubeVizUnit
        #        so that new widgets are populated.
        if component_id in self.controller_components:
            cubeviz_unit = self.controller_components[component_id]
            self.current_unit = cubeviz_unit

            wave = self.controller.wave
            pixel_area = self.controller.pixel_area
            layout = assign_cubeviz_unit_layout(cubeviz_unit,
                                                wave=wave,
                                                pixel_area=pixel_area)
            layout.set_message_box(self.message_box)
            layout.populate_unit_layout(self.unit_layout, self)
            self.current_layout = layout
            if ASTROPY_CubeVizUnit == cubeviz_unit.type:
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

    def convert_displayed_units(self):
        """
        Calls CubeVizUnit.change_units to finalize
        conversions. Updates plots with new units.
        :return:
        """
        success = self.current_layout.change_units()
        if not success:
            info = QMessageBox.critical(self, "Error", "Conversion failed.")
            return

        new_unit = self.current_layout.new_unit
        self.current_unit.unit = new_unit
        self.current_unit.unit_string = str(new_unit)

        component_id = self.component_combo.currentData()
        self.data.get_component(component_id).units = self.current_unit.unit_string
        msg = FluxUnitsUpdateMessage(self, self.current_unit, component_id)
        self._hub.broadcast(msg)
        self.close()

    def convert_data_units(self):
        """
        Calls CubeVizUnit.change_units to finalize
        conversions. Updates plots with new units.
        :return:
        """
        success = self.current_layout.change_units()
        if not success:
            info = QMessageBox.critical(self, "Error", "Conversion failed.")
            return

        new_unit = self.current_layout.new_unit
        self.current_unit.unit = new_unit
        self.current_unit.unit_string = str(new_unit)

        component_id = self.component_combo.currentData()
        component = component_id.parent.get_component(component_id)

        old_array = component._data.copy()
        old_array.flags.writeable = True

        wavelengths = self.controller.construct_3d_wavelengths(old_array)

        new_array = self.current_unit.convert_value(old_array, wave=wavelengths)

        component._data = new_array

        self.current_unit = self.controller.add_component_unit(component_id, new_unit)
        component.units = self.current_unit.unit_string
        msg = FluxUnitsUpdateMessage(self, self.current_unit, component_id)
        self._hub.broadcast(msg)
        self.close()

    def cancel(self):
        self.close()
