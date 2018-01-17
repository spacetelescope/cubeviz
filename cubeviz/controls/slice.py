import numpy as np
from specviz.third_party.glue.data_viewer import dispatch as specviz_dispatch

RED_BACKGROUND = "background-color: rgba(255, 0, 0, 128);"

class SliceController:

    def __init__(self, cubeviz_layout):
        self._cv_layout = cubeviz_layout
        ui = cubeviz_layout.ui

        # These are the contents of the text boxes
        self._slice_textbox = ui.slice_textbox
        self._wavelength_textbox = ui.wavelength_textbox

        # This is the slider widget itself
        self._slice_slider = ui.slice_slider

        # This is the label for the wavelength units
        self._wavelength_textbox_label = ui.wavelength_textbox_label

        self._slice_slider.valueChanged.connect(self._on_slider_change)
        self._slice_textbox.returnPressed.connect(self._on_text_slice_change)
        self._wavelength_textbox.returnPressed.connect(self._on_text_wavelength_change)

        self._slice_slider.setEnabled(False)
        self._slice_textbox.setEnabled(False)
        self._wavelength_textbox.setEnabled(False)

        self._wavelength_format = '{}'
        self._wavelength_units = None
        self._wavelengths = None

        # Connect this class to specviz's event dispatch so methods can listen
        # to specviz events
        specviz_dispatch.setup(self)


    def enable(self, wcs, wavelengths):
        """
        Setup the slice slider (min/max, units on description and initial position).

        :return:
        """
        self._slice_slider.setEnabled(True)
        self._slice_textbox.setEnabled(True)
        self._wavelength_textbox.setEnabled(True)

        self._slice_slider.setMinimum(0)

        # Store the wavelength units and format
        self._wavelength_units = str(wcs.wcs.cunit[2])
        self._wavelength_format = '{:.3}'
        self._wavelength_textbox_label.setText('Wavelength ({})'.format(self._wavelength_units))

        # Grab the wavelengths so they can be displayed in the text box
        self._wavelengths = wavelengths
        self._slice_slider.setMaximum(len(self._wavelengths) - 1)

        # Set the default display to the middle of the cube
        middle_index = len(self._wavelengths) // 2
        self._update_slice_textboxes(middle_index)
        self._slice_slider.setValue(middle_index)
        self._wavelength_textbox.setText(self._wavelength_format.format(self._wavelengths[middle_index]))

        self._cv_layout.synced_index = middle_index

    def update_index(self, index):
        self._slice_slider.setValue(index)
        self._update_slice_textboxes(index)


    def _on_slider_change(self, event):
        """
        Callback for change in slider value.

        :param event:
        :return:
        """
        index = self._slice_slider.value()
        cube_views = self._cv_layout.cube_views
        active_cube = self._cv_layout._active_cube
        active_widget = active_cube._widget

        # Update the image displayed in the slice in the active view
        active_widget.update_slice_index(index)

        # If the active widget is synced then we need to update the image
        # in all the other synced views.
        if active_widget.synced and not self._cv_layout._single_viewer_mode:
            for view in cube_views:
                if view != active_cube and view._widget.synced:
                    view._widget.update_slice_index(index)
            self._cv_layout.synced_index = index

        # Now update the slice and wavelength text boxes
        self._update_slice_textboxes(index)

        specviz_dispatch.changed_dispersion_position.emit(pos=index)


    def _update_slice_textboxes(self, index):
        """
        Update the slice index number text box and the wavelength value displayed in the wavelengths text box.

        :param index: Slice index number displayed.
        :return:
        """

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

        # If a number and out of range then set to the first or last slice
        # depending if they set the number too low or too high.
        if index < 0:
            index = 0
        if index > len(self._wavelengths) - 1:
            index = len(self._wavelengths) - 1

        # Now update the slice and wavelength text boxes
        self._update_slice_textboxes(index)

        # Update the slider.
        self._slice_slider.setValue(index)


    @specviz_dispatch.register_listener("change_dispersion_position")
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

        # Now update the slice and wavelength text boxes
        self._update_slice_textboxes(index)

        # Update the slider.
        self._slice_slider.setValue(index)
