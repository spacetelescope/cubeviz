from astropy import units as u
from specviz.third_party.glue.data_viewer import dispatch as specviz_dispatch

from ..messages import WavelengthUpdateMessage, WavelengthUnitUpdateMessage, RedshiftUpdateMessage


OBS_WAVELENGTH_TEXT = 'Obs Wavelength'
REST_WAVELENGTH_TEXT = 'Rest Wavelength'


class UnitController:
    def __init__(self, cubeviz_layout):
        self._cv_layout = cubeviz_layout
        self._hub = cubeviz_layout.session.hub
        ui = cubeviz_layout.ui
        self._wavelengths = []
        self._original_wavelengths = []
        self._original_units = u.m
        # TODO: code debt: rename _new_units to something else
        self._new_units = self._original_units

        # Add the redshift z value
        self._redshift_z = 0

        # This is the Wavelength conversion/combobox code
        self._units = [u.m, u.cm, u.mm, u.um, u.nm, u.AA]
        self._units_titles = list(u.long_names[0].title() for u in self._units)

        # This is the label for the wavelength units
        self._wavelength_textbox_label = ui.wavelength_textbox_label.text()

        specviz_dispatch.setup(self)

    def enable(self, units, wavelength):
        self._wavelengths = wavelength
        self._original_wavelengths = wavelength
        self._send_wavelength_message(wavelength)
        self._send_wavelength_unit_message(units)

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

    @specviz_dispatch.register_listener("change_redshift")
    def specviz_change_redshift(self, redshift):
        """
        Change the redshift based on a message from specviz.

        :paramter: redshift - the Z value.
        :return: nothing
        """
        self.update_redshift(redshift)

    def update_units(self, units):

        # TODO: update internal unit representation here?
        self._send_wavelength_unit_message(units)

        self._wavelengths = (self._wavelengths * self._new_units).to(units) / units

        specviz_dispatch.changed_units.emit(x=units)

    def update_redshift(self, redshift, label=''):
        # If the input redshift is the current value we have then we are not
        # going to do anything.
        if self._redshift_z == redshift:
            return

        if redshift is not None and redshift != 0:
            self._wavelength_textbox_label = REST_WAVELENGTH_TEXT
        else:
            self._wavelength_textbox_label = OBS_WAVELENGTH_TEXT

        self._wavelengths = (1 + redshift) * self._original_wavelengths

        # This calls the setter above, so really, the magic is there.
        self._redshift_z = redshift
        self._send_redshift_message(redshift)

        specviz_dispatch.change_redshift.emit(redshift=redshift)

    def _send_wavelength_message(self, wavelengths):
        msg = WavelengthUpdateMessage(self, wavelengths)
        self._hub.broadcast(msg)

    def _send_wavelength_unit_message(self, units):
        msg = WavelengthUnitUpdateMessage(self, units)
        self._hub.broadcast(msg)

    def _send_redshift_message(self, redshift):
        msg = RedshiftUpdateMessage(self, redshift, label=self.wavelength_label)
        self._hub.broadcast(msg)

    def convert_wavelengths(self, old_wavelengths, old_units, new_units):
        if old_wavelengths is not None:
            new_wavelengths = ((old_wavelengths * old_units).to(new_units) / new_units)
            return new_wavelengths
        return False

    def get_new_units(self):
        return self._new_units
