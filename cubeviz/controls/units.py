import os
import yaml
import warnings

from qtpy.QtCore import Qt, Signal, QThread
from qtpy.QtWidgets import (
    QDialog, QApplication, QPushButton, QProgressBar,
    QLabel, QWidget, QDockWidget, QHBoxLayout, QVBoxLayout,
    QComboBox, QMessageBox, QLineEdit, QRadioButton, QWidgetItem
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


class CubeVizUnit:
    def __init__(self, unit=None, unit_string=""):
        self._unit = unit
        self._unit_string = unit_string
        self._type = "CubeVizUnit"
        self.is_convertable = False

    @property
    def unit(self):
        return self._unit

    @property
    def unit_string(self):
        return self._unit_string

    @property
    def type(self):
        return self._type

    def populate_unit_layout(self, unit_layout):
        #default_message = "CubeViz can not convert this unit."
        default_message = self.unit_string
        default_label = QLabel(default_message)
        unit_layout.addWidget(default_label)
        return unit_layout


class FormattedUnit(CubeVizUnit):
    def __init__(self, unit, unit_string,
                 numeric, spectral_flux_density, area):
        super(FormattedUnit, self).__init__()
        self._unit = unit
        self._unit_string = unit_string
        self.numeric = numeric
        self.spectral_flux_density = spectral_flux_density
        self.area = area
        self._type = "FormattedUnit"
        self.is_convertable = True


class SpectralFluxDensity(CubeVizUnit):
    def __init__(self, unit, unit_string, spectral_flux_density):
        super(SpectralFluxDensity, self).__init__()
        self._unit = unit
        self._unit_string = unit_string
        self.spectral_flux_density = spectral_flux_density
        self._type = "SpectralFluxDensity"
        self.is_convertable = True


class UnknownUnit(CubeVizUnit):
    def __init__(self, unit, unit_string):
        super(UnknownUnit, self).__init__()
        self._unit = unit
        self._unit_string = unit_string
        self._type = "UnknownUnit"
        self.is_convertable = False


class NoneUnit(CubeVizUnit):
    def __init__(self):
        super(NoneUnit, self).__init__()
        self._unit = None
        self._unit_string = ""
        self._type = "NoneUnit"
        self.is_convertable = False


class ConvertFluxUnitGUI(QDialog):
    def __init__(self, controller, parent=None):
        super(ConvertFluxUnitGUI, self).__init__(parent=parent)
        self.title = "Smoothing Selection"

        self.controller = controller
        self.data = controller.data
        self.controller_components = controller.components

        self._init_ui()

    def _init_ui(self):
        # LINE 1: Data component drop down
        self.component_prompt = QLabel("Data Component:")
        self.component_prompt.setWordWrap(True)
        self.component_prompt.setMinimumWidth(150)
        # Add the data component labels to the drop down, with the ComponentID
        # set as the userData:
        if self.parent is not None and hasattr(self.parent, 'data_components'):
            self.label_data = [(str(cid), str(cid)) for cid in self.parent.data_components]
        else:
            self.label_data = [(str(cid), str(cid)) for cid in self.data.visible_components]

        default_index = 0
        self.component_combo = QComboBox()
        update_combobox(self.component_combo, self.label_data, default_index=default_index)
        self.component_combo.currentIndexChanged.connect(self.update_unit_layout)

        # hbl is short for Horizontal Box Layout
        hbl1 = QHBoxLayout()
        hbl1.addWidget(self.component_prompt)
        hbl1.addWidget(self.component_combo)

        # LINE 2: Unit conversion layout
        self.unit_layout = QHBoxLayout()  # this is hbl2

        # Line 3: Buttons
        self.okButton = QPushButton("Convert Units")
        self.okButton.clicked.connect(self.call_main)
        self.okButton.setDefault(True)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel)

        hbl3 = QHBoxLayout()
        hbl3.addStretch(1)
        hbl3.addWidget(self.cancelButton)
        hbl3.addWidget(self.okButton)

        vbl = QVBoxLayout()
        vbl.addLayout(hbl1)
        vbl.addLayout(self.unit_layout)
        vbl.addLayout(hbl3)
        self.setLayout(vbl)
        self.vbl = vbl

        self.update_unit_layout(default_index)

        self.show()

    def update_unit_layout(self, index):
        component_id = str(self.component_combo.currentData())

        widgets = (self.unit_layout.itemAt(i) for i in range(self.unit_layout.count()))
        for w in widgets:
            if isinstance(w,QWidgetItem):
                w = w.widget()
            self.unit_layout.removeWidget(w)
            w.deleteLater()

        if component_id in self.controller_components:
            cubeviz_unit = self.controller_components[component_id]
            cubeviz_unit.populate_unit_layout(self.unit_layout)
            if cubeviz_unit.is_convertable:
                self.okButton.setEnabled(True)
            else:
                self.okButton.setEnabled(False)
        else:
            default_message = "CubeViz can not convert this unit."
            default_label = QLabel(default_message)
            self.unit_layout.addWidget(default_label)
            self.okButton.setEnabled(False)

        self.unit_layout.update()
        self.vbl.update()

    def call_main(self):
        pass

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
                u.add_enabled_units(new_astropy_unit)

        self.registered_units = cfg["registered_units"]

        self.data = None
        self.components = {}

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
            numeric = self.string_to_unit(registered_unit["numeric"])
            spectral_flux_density = self.string_to_unit(registered_unit["spectral_flux_density"])
            area = self.string_to_unit(registered_unit["area"])
            cubeviz_unit = FormattedUnit(astropy_unit, unit_string,
                                         numeric, spectral_flux_density, area)
        else:
            astropy_unit = self.string_to_unit(unit_string)
            if 'spectral flux density' in astropy_unit.physical_type:
                cubeviz_unit = SpectralFluxDensity(astropy_unit, unit_string, astropy_unit)
            else:
                cubeviz_unit = UnknownUnit(astropy_unit, unit_string)
        self.components[component_id] = cubeviz_unit
        return cubeviz_unit

    def remove_component_unit(self, component_id):
        component_id = str(component_id)
        if component_id in self.components:
            del self.components[component_id]

    def get_component_unit(self, component_id):
        component_id = str(component_id)
        if component_id in self.components:
            return self.components[component_id].unit
        return None

    def set_data(self, data):
        self.data = data
        self.components = {}
        for comp in data.visible_components:
            self.add_component_unit(comp, data.get_component(comp).units)

    def converter(self, parent=None):
        ex = ConvertFluxUnitGUI(self, parent)
