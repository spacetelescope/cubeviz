import os
import yaml

from astropy import units as u

DEFAULT_FLUX_UNITS_CONFIGS = os.path.join(os.path.dirname(__file__), 'registered_flux_units.yaml')


def _is_duplicate(unit_list, current_unit):
    """
    Given a list of units, add target units
    after checking for duplicates
    :param unit_list: list of units or string
    :param target_unit: unit or string
    :return: updated unit
    """

    # Make both a string and astropy version
    if isinstance(current_unit, str):
        current_unit = u.Unit(current_unit)

    # Create list of all astropy Unit things
    temp_list = [unit if not isinstance(unit, str) else u.Unit(unit) for unit in unit_list]

    # check to see if current_unit is in there
    return any([unit.to_string() == current_unit.to_string() for unit in temp_list])


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

    def compose_unit_list(self, current_unit=None):
        """
        Returns a list of unit strings in the registry.
        Adds current_unit if not duplicated. Registered
        units are added first.
        :param current_unit: Unit or unit str
        :return: list of unit str
        """
        unit_list = self._locally_defined_units()  # final list

        for unit in self.runtime_defined_units:
            if not _is_duplicate(unit_list, unit):
                unit_list.append(unit)

        if current_unit is not None:
            if not _is_duplicate(unit_list, current_unit):
                unit_list.append(current_unit)
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
        else:
            raise TypeError("Expected unit or string, got {} instead".format(type(item)))


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
        self.runtime_solid_angle_units = []  # Stores list of runtime angle unitsa
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

    def compose_unit_list(self, pixel_only=False,
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
        unit_list = []  # final list
        item_list = []  # runtime def units
        if not solid_angle_only:
            unit_list.extend(self._locally_defined_pixel_units())
            item_list.extend(self.runtime_pixel_units)
        if not pixel_only:
            unit_list.extend(self._locally_defined_solid_angle_units())
            item_list.extend(self.runtime_solid_angle_units)

        for unit in item_list:
            if not _is_duplicate(unit_list, unit):
                unit_list.append(unit)

        if current_unit is not None:
            if not _is_duplicate(unit_list, current_unit):
                unit_list.append(current_unit)
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
        else:
            raise TypeError("Expected unit or string, got {} instead".format(type(item)))

    def add_solid_angle_unit(self, item):
        """
        Add new solid angle unit
        :param item: unit or unit str
        """
        if isinstance(item, str) \
                or isinstance(item, u.UnitBase):
            if item not in self.runtime_solid_angle_units:
                self.runtime_solid_angle_units.append(item)
        else:
            raise TypeError("Expected unit or string, got {} instead".format(type(item)))

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
        elif 'solid angle' in new_unit.physical_type.lower():
            self.add_solid_angle_unit(new_unit)
        else:
            raise ValueError("Expected pixel or solid angle unit but got {}".format(new_unit.physical_type))


def register_new_unit(new_unit):
    """
    Add new unit to astropy.units
    :param new_unit: astropy unit
    """
    global AREA_UNIT_REGISTRY, FLUX_UNIT_REGISTRY
    u.add_enabled_units(new_unit)
    if FLUX_UNIT_REGISTRY.is_compatible(new_unit):
        FLUX_UNIT_REGISTRY.add_unit(new_unit)
    if new_unit.decompose() == u.pix.decompose() or \
            'solid angle' in new_unit.physical_type.lower():
        AREA_UNIT_REGISTRY.add_unit(new_unit)


def setup_registered_units():
    """
    Function to setup predefined units.
    This should run once when the module
    is imported.
    """
    global FORMATTED_UNITS
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
            register_new_unit(new_astropy_unit)

    new_physical_types = [
        [(u.Jy / u.degree ** 2), 'SFD_over_solid_angle'],
        [(u.Jy / u.pix), 'SFD_over_pix']
    ]

    for model_unit, name in new_physical_types:
        try:
            u.def_physical_type(model_unit, name)
        except ValueError:
            continue

    FORMATTED_UNITS = cfg["formatted_units"]


FLUX_UNIT_REGISTRY = FluxUnitRegistry()
AREA_UNIT_REGISTRY = AreaUnitRegistry()
FORMATTED_UNITS = {}

# Call setup_registered_units on start up:
setup_registered_units()

# CubeViz Unit types:
NONE_CubeVizUnit = "NONE"
UNKNOWN_CubeVizUnit = "UNKNOWN"
ASTROPY_CubeVizUnit = "ASTROPY"
CUBEVIZ_UNIT_TYPES = [NONE_CubeVizUnit, UNKNOWN_CubeVizUnit, ASTROPY_CubeVizUnit]
