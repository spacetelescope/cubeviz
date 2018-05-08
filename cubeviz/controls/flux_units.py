import warnings

import numpy as np

from astropy.utils.exceptions import AstropyWarning
from astropy import units as u
from astropy.units.quantity import Quantity
from astropy.wcs.utils import proj_plane_pixel_area

from .flux_unit_registry import FLUX_UNIT_REGISTRY, AREA_UNIT_REGISTRY, FORMATTED_UNITS
from .flux_units_gui import ConvertFluxUnitGUI

CUBEVIZ_UNIT_TYPES = ["NONE", "UNKNOWN", "ASTROPY"]


class CubeVizUnit:
    def __init__(self, unit=None,
                 unit_string="",
                 component_id=None,
                 unit_type="NONE"):
        self._controller = None  # Unit controller (property)
        self._original_unit = unit  # the data's actual units
        self._original_unit_string = unit_string  # original_unit as str
        self._unit = unit  # Current Unit
        self._unit_string = unit_string  # unit as str
        self._type = unit_type  # Type of CubeVizUnit
        self.component_id = component_id  # Glue component ID

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, unit):
        self._unit = unit

    @property
    def unit_string(self):
        return self._unit_string

    @unit_string.setter
    def unit_string(self, unit_string):
        if isinstance(unit_string, str):
            self._unit_string = unit_string

    @property
    def original_unit(self):
        return self._original_unit

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, unit_type):
        if isinstance(type, str):
            self._type = unit_type

    @property
    def controller(self):
        return self._controller

    @controller.setter
    def controller(self, controller):
        self._controller = controller

    def convert_value(self, value, wave=None, new_unit=None):
        if isinstance(value, Quantity):
            value = value.value
        elif not isinstance(value, int) \
                and not isinstance(value, float) \
                and not isinstance(value, np.ndarray):
            raise ValueError("Expected float or int, got {} instead.".format(type(value)))

        if "NONE" == self.type:
            return value

        new_value = value

        if not new_unit:
            new_unit = self._unit

        if hasattr(u.spectral_density, "pixel_area"):
            u.spectral_density.pixel_area = self.controller.pixel_area

        if wave is not None:
            new_value *= self._original_unit.to(new_unit, equivalencies=u.spectral_density(wave))
        else:
            new_value *= self._original_unit.to(new_unit)

        if isinstance(new_value, Quantity):
            new_value = new_value.value

        return new_value

    def convert_from_original_unit(self, value, wave=None):
        return self.convert_value(value, wave=wave)


class FluxUnitController:
    def __init__(self, cubeviz_layout=None):
        self.cubeviz_layout = cubeviz_layout
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
            pixel_area = (proj_plane_pixel_area(self.wcs) * (top_unit ** 2) / u.pix).to(u.arcsec ** 2 / u.pix)
            return pixel_area
        except (ValueError, AttributeError):
            return None

    @property
    def wave(self):
        if self.cubeviz_layout:
            return self.cubeviz_layout.get_wavelength()
        return None

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
        elif isinstance(unit, Quantity):
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
            astropy_unit = None
            unit_string = ""
            unit_type = "NONE"
        # ELSE IF: formatted unit
        elif unit_string in FORMATTED_UNITS:
            registered_unit = FORMATTED_UNITS[unit_string]
            if "astropy_unit_string" in registered_unit:
                unit_string = registered_unit["astropy_unit_string"]
            astropy_unit = self.string_to_unit(unit_string)
            unit_type = "ASTROPY"
        else:
            astropy_unit = self.string_to_unit(unit_string)
            # IF: no astropy unit component
            if astropy_unit is None:
                unit_type = "UNKNOWN"
            else:
                unit_type = "ASTROPY"

        cubeviz_unit = CubeVizUnit(unit=astropy_unit,
                                   unit_string=unit_string,
                                   component_id=component_id,
                                   unit_type=unit_type)

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

    def converter(self, parent=None):
        """
        Launch Converter GUI
        :param parent: application
        :return: ConvertFluxUnitGUI instance
        """

        if hasattr(u.spectral_density, "pixel_area"):
            u.spectral_density.pixel_area = self.pixel_area

        ex = ConvertFluxUnitGUI(self, parent)
        return ex
