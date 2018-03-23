import os
import yaml

import warnings
from astropy.utils.exceptions import AstropyWarning
from astropy import units as u

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

        # This is the Wavelength conversion/combobox code
        self.units = [u.m, u.cm, u.mm, u.um, u.nm, u.AA]
        self.units_titles = list(u.long_names[0].title() for u in self.units)

        # This is the label for the wavelength units
        self._wavelength_textbox_label = ui.wavelength_textbox_label

    def on_combobox_change(self, new_unit_name):
        """
        Callback for change in unitcombobox value
        :param event:
        :return:
        """
        # Get the new unit name from the selected value in the comboBox and
        # set that as the new unit that wavelengths will be converted to
        # new_unit_name = self._wavelength_combobox.currentText()
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

    def get_new_units(self):
        return self._new_units


class CubeVizUnit:

    def __init__(self, unit=None, unit_string=""):
        self._unit = unit
        self._unit_string = unit_string

    @property
    def unit(self):
        return self._unit

    @property
    def unit_string(self):
        return self._unit_string


class FormattedUnit(CubeVizUnit):
    def __init__(self, unit, unit_string,
                 numeric, spectral_flux_density, area):
        super(FormattedUnit, self).__init__()
        self._unit = unit
        self._unit_string = unit_string
        self.numeric = numeric
        self.spectral_flux_density = spectral_flux_density
        self.area = area
        self.type = "FormattedUnit"


class SpectralFluxDensity(CubeVizUnit):
    def __init__(self, unit, unit_string, spectral_flux_density):
        super(SpectralFluxDensity, self).__init__()
        self._unit = unit
        self._unit_string = unit_string
        self.spectral_flux_density = spectral_flux_density
        self.type = "SpectralFluxDensity"


class UnknownUnit(CubeVizUnit):
    def __init__(self, unit, unit_string):
        super(UnknownUnit, self).__init__()
        self._unit = unit
        self._unit_string = unit_string
        self.type = "UnknownUnit"


class NoneUnit(CubeVizUnit):
    def __init__(self):
        super(NoneUnit, self).__init__()
        self._unit = None
        self._unit_string = ""
        self.type = "NoneUnit"


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
