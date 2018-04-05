import numpy as np

from glue.core import HubListener
from specviz.third_party.glue.data_viewer import dispatch as specviz_dispatch

from ..messages import (SliceIndexUpdateMessage, WavelengthUpdateMessage,
                        WavelengthUnitUpdateMessage, RedshiftUpdateMessage)
from .wavelengths import REST_WAVELENGTH_TEXT, OBS_WAVELENGTH_TEXT

RED_BACKGROUND = "background-color: rgba(255, 0, 0, 128);"

import logging
logging.basicConfig(format='%(levelname)-6s: %(name)-10s %(asctime)-15s  %(message)s')
log = logging.getLogger("SliceController")
log.setLevel(logging.DEBUG)

class SliceController(HubListener):

    def __init__(self, cubeviz_layout):
        self._cv_layout = cubeviz_layout
        self._hub = cubeviz_layout.session.hub
        ui = cubeviz_layout.ui

        # These are the contents of the text boxes
        self._slice_textbox = ui.slice_textbox
        self._wavelength_textbox = ui.wavelength_textbox

        # This is the slider widget itself
        self._slice_slider = ui.slice_slider

        # This is the label for the wavelength units
        self._wavelength_textbox_label = ui.wavelength_textbox_label

        self._slice_slider.valueChanged.connect(self._on_slider_change)
        self._slice_slider.sliderPressed.connect(self._on_slider_pressed)
        self._slice_slider.sliderReleased.connect(self._on_slider_released)
        self._slider_flag = False

        self._slice_textbox.returnPressed.connect(self._on_text_slice_change)
        self._wavelength_textbox.returnPressed.connect(self._on_text_wavelength_change)

        self._slice_slider.setEnabled(False)
        self._slice_textbox.setEnabled(False)
        self._wavelength_textbox.setEnabled(False)
        self._wavelength_textbox_label.setWordWrap(True)

        # This should be used to distinguised between observed and rest wavelengths
        # We are not going to enforce what the name should be at this level.
        self._wavelength_label_text = OBS_WAVELENGTH_TEXT

        self._wavelength_format = '{:.3}'
        self._wavelength_units = None
        self._wavelengths = None

        # Tracks the index of the synced viewers
        self.synced_index = None

        # Connect this class to specviz's event dispatch so methods can listen
        # to specviz events
        specviz_dispatch.setup(self)

    def enable(self):
        """
        Setup the slice slider (min/max, units on description and initial position).

        :return:
        """
        self.set_enabled(True)

        self._hub.subscribe(self, SliceIndexUpdateMessage, handler=self._handle_index_update)
        self._hub.subscribe(self, WavelengthUpdateMessage, handler=self._handle_wavelength_update)
        self._hub.subscribe(self, WavelengthUnitUpdateMessage, handler=self._handle_wavelength_units_update)
        self._hub.subscribe(self, RedshiftUpdateMessage, handler=self._handle_redshift_update)

        self._slice_slider.setMinimum(0)

    def _handle_wavelength_units_update(self, message):

        # Store the wavelength units and format
        self._wavelength_units = message.units
        self._wavelength_textbox_label.setText('{} ({})'.format(
            self._wavelength_label_text, self._wavelength_units))

    def _handle_wavelength_update(self, message):

        # Grab the wavelengths so they can be displayed in the text box
        self._wavelengths = message.wavelengths
        self._slice_slider.setMaximum(len(self._wavelengths) - 1)

        if self.synced_index is None:
            # Set the initial display to the middle of the cube
            middle_index = len(self._wavelengths) // 2
            self._slice_slider.setValue(middle_index)
            self.synced_index = middle_index

        index = self._cv_layout._active_cube._widget.slice_index
        self._wavelength_textbox.setText(self._wavelength_format.format(self._wavelengths[index]))

    def _handle_redshift_update(self, message):

        self._wavelength_label_text = message.label

        self._wavelength_textbox_label.setText('{} ({})'.format(
            self._wavelength_label_text, self._wavelength_units))

    def set_enabled(self, value):
        self._slice_slider.setEnabled(value)
        self._slice_textbox.setEnabled(value)
        self._wavelength_textbox.setEnabled(value)

    def update_index(self, index):
        self._slice_slider.setValue(index)

    def change_slider_value(self, amount):
        new_index = self._slice_slider.value() + amount
        self._slice_slider.setValue(new_index)

        specviz_dispatch.changed_dispersion_position.emit(pos=new_index)

    def _handle_index_update(self, message):
        index = message.index

        try:
            tb_index = int(self._slice_textbox.text())
        except ValueError:
            tb_index = -1

        if tb_index != index:
            self._slice_textbox.setText(str(index))

        try:
            wavelength = float(self._wavelength_textbox.text())
            wv_index = np.argsort(abs(self._wavelengths - wavelength))[0]
        except ValueError:
            wavelength = -1
            wv_index = -1

        self._wavelength_textbox.setText(self._wavelength_format.format(self._wavelengths[index]))

        slider_index = self._slice_slider.value()
        if slider_index != index:
            self._slice_slider.setValue(index)

        if self._cv_layout._active_cube._widget.synced:
            self.synced_index = index

        specviz_dispatch.changed_dispersion_position.emit(pos=index)

    def _on_slider_change(self, event):
        """
        Callback for change in slider value.

        :param event:
        :return:
        """
        index = self._slice_slider.value()
        self._send_index_message(index)

    def _send_index_message(self, index):
        msg = SliceIndexUpdateMessage(self, index,
                                      self._cv_layout.session.data_collection[0],
                                      slider_down=self._slider_flag)
        self._hub.broadcast(msg)

    def _on_slider_pressed(self):
        """
        Callback for slider pressed.
        activates fast_draw_slice_at_index flags
        """
        # This flag will activate fast_draw_slice_at_index
        # Which will redraw sliced images quickly
        self._slider_flag = True

    @specviz_dispatch.register_listener("finished_position_change")
    def _on_slider_released(self):
        """
        Callback for slider released (includes specviz slider).
        Dactivates fast_draw_slice_at_index flags
        Will do a full redraw of all synced viewers.
        This is considered the final redraw after fast_draw_slice_at_index
        blits images to the viewers. This function will redraw the axis,
        tites, labels etc...
        """
        # This flag will deactivate fast_draw_slice_at_index
        self._slider_flag = False

        index = self._slice_slider.value()
        self._send_index_message(index)
        specviz_dispatch.changed_dispersion_position.emit(pos=index)

    #@glue_subscribe(SliceIndexUpdateMessage)
    def _update_slice_textboxes(self, message):
        """
        Update the slice index number text box and the wavelength value displayed in the wavelengths text box.

        :param index: Slice index number displayed.
        :return:
        """
        index = message.index

        # Update the input text box for slice number
        self._slice_textbox.setText(str(index))

        # Update the wavelength for the corresponding slice number.
        self._wavelength_textbox.setText(self._wavelength_format.format(self._wavelengths[index]))

    def _on_text_slice_change(self, event=None):
        """
        Callback for a change in the slice index text box.  We will need to
        update the slider and the wavelength value when this changes.

        :param event:
        :return:
        """
        # Get the value they typed in, but if not a number, then let's just use
        # the first slice.
        try:
            index = int(self._slice_textbox.text())
            self._slice_textbox.setStyleSheet("")
        except ValueError:
            self._slice_textbox.setStyleSheet(RED_BACKGROUND)
            return

        if index == self._slice_textbox.text():
            return

        # If a number and out of range then set to the first or last slice
        # depending if they set the number too low or too high.
        if index < 0:
            index = 0
        if index > len(self._wavelengths) - 1:
            index = len(self._wavelengths) - 1

        self._send_index_message(index)

    def _on_text_wavelength_change(self, event=None, pos=None):
        """
        Callback for a change in wavelength input box. We want to find the
        closest wavelength and use the index of it.  We will need to update the
        slice index box and slider as well as the image.

        :param event:
        :param pos: This is the argument used by the specviz event listener to
                    update the CubeViz slider and associated text based on the
                    movement of the SpecViz position bar. The name of this
                    argument cannot change since it is the one expected by the
                    SpecViz event system.
        :return:
        """
        try:
            # Find the closest real wavelength and use the index of it
            wavelength = pos if pos is not None else float(self._wavelength_textbox.text())
            index = np.argsort(abs(self._wavelengths - wavelength))[0]
            self._wavelength_textbox.setStyleSheet("")
        except ValueError:
            self._wavelength_textbox.setStyleSheet(RED_BACKGROUND)
            return

        self._send_index_message(index)

    @specviz_dispatch.register_listener("change_dispersion_position")
    def specviz_wavelength_slider_change(self, event=None, pos=None):
        """
        SpecViz slider index changed callback
        """
        # if self._slider_flag is active then
        # something else is using it so don't
        # deactivate it when done (deactivate_flag)
        if self._slider_flag:
            deactivate_flag = False
        else:
            deactivate_flag = True
            self._slider_flag = True

        # The "pos" value coming from specviz appears to be related to the
        # index in the observed wavelength and so if there is a redshift
        # then we need to convert the pos to the rest wavelength position.
        if self._cv_layout._wavelength_controller and not self._cv_layout._wavelength_controller.redshift_z == 0.0:
            rest_wavelength = pos / (1 + self._cv_layout._wavelength_controller.redshift_z)
            pos = np.argsort(abs(self._wavelengths - rest_wavelength))[0]

            # Pos is a wavelength and not an index for the call back for specviz
            pos = self._wavelengths[pos]

        self._on_text_wavelength_change(event, pos)

        if deactivate_flag:
            self._slider_flag = False
