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

        self._send_wavelength_message()

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

    def _send_wavelength_message(self, wavelengths):
        msg = WavelengthUpdateMessage(self, wavelengths)
        self._hub.broadcast(msg)

    def _send_wavelength_unit_message(self, units):
        print("_send_wavelength_unit_message")
        msg = WavelengthUnitUpdateMessage(self, units)
        self._hub.broadcast(msg)

    def _send_redshift_message(self, redshift):
        print("_send_redshift_message")
        msg = RedshiftUpdateMessage(self, redshift)
        self._hub.broadcast(msg)

    def convert_wavelengths(self, old_wavelengths, old_units, new_units):
        if old_wavelengths is not None:
            new_wavelengths = ((old_wavelengths * old_units).to(new_units) / new_units)
            return new_wavelengths
        return False

    def get_new_units(self):
        return self._new_units
