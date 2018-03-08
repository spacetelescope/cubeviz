from __future__ import absolute_import, division, print_function

from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy.QtWidgets import (
    QDialog, QApplication, QPushButton,
    QLabel, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox
)

from astropy.stats import sigma_clip
import numpy as np
import re

class WavelengthUI(QDialog):
    def __init__(self, wavelength_units=['mm', 'cm'], parent=None):
        super(WavelengthUI,self).__init__(parent)

        self.setWindowTitle("Wavelengths")

        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.title = "Wavelengths"

        self._general_description = "Choose the wavelength units and/or set a red-shift."

        self.wavelength_units = wavelength_units
        self.currentAxes = None
        self.currentKernel = None

        self.createUI()

    def createUI(self):
        """
        Create the popup box with the calculation input area and buttons.

        :return:
        """
        boldFont = QtGui.QFont()
        boldFont.setBold(True)

        # Create data component label and input box
        self.widget_desc = QLabel(self._general_description)
        self.widget_desc.setWordWrap(True)
        self.widget_desc.setFixedWidth(350)
        self.widget_desc.setAlignment((Qt.AlignLeft | Qt.AlignTop))

        hb_desc = QHBoxLayout()
        hb_desc.addWidget(self.widget_desc)

        # Create wavelength units component label and input box
        self.wavelengthunits_label = QLabel("Wavelength Units:")
        self.wavelengthunits_label.setFixedWidth(100)
        self.wavelengthunits_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.wavelengthunits_label.setFont(boldFont)

        self.wavelengthunits_combobox = QComboBox()
        self.wavelengthunits_combobox.addItems(self.wavelength_units)
        self.wavelengthunits_combobox.setMinimumWidth(200)

        hb_wavelengthunits = QHBoxLayout()
        hb_wavelengthunits.addWidget(self.wavelengthunits_label)
        hb_wavelengthunits.addWidget(self.wavelengthunits_combobox)

        # Create redshift label and input box
        self.redshift_label = QLabel("RedShift:")
        self.redshift_label.setFixedWidth(100)
        self.redshift_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.redshift_label.setFont(boldFont)

        self.redshift_combobox = QLineEdit()
        self.redshift_combobox.setMinimumWidth(200)

        hb_redshift = QHBoxLayout()
        hb_redshift.addWidget(self.redshift_label)
        hb_redshift.addWidget(self.redshift_combobox)

        # Create wavelength units component label and input box
        self.wavelengthdisplay_label = QLabel("Wavelength Display:")
        self.wavelengthdisplay_label.setFixedWidth(100)
        self.wavelengthdisplay_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.wavelengthdisplay_label.setFont(boldFont)

        self.wavelengthdisplay_combobox = QComboBox()
        self.wavelengthdisplay_combobox.addItems(['Obs Wavelengths', 'Rest Wavelengths'])
        self.wavelengthdisplay_combobox.setMinimumWidth(200)

        hb_wavelengthdisplay = QHBoxLayout()
        hb_wavelengthdisplay.addWidget(self.wavelengthdisplay_label)
        hb_wavelengthdisplay.addWidget(self.wavelengthdisplay_combobox)

        # Create error label
        self.error_label = QLabel("")
        self.error_label.setFixedWidth(100)

        self.error_label_text = QLabel("")
        self.error_label_text.setMinimumWidth(200)
        self.error_label_text.setAlignment((Qt.AlignLeft | Qt.AlignTop))

        hbl_error = QHBoxLayout()
        hbl_error.addWidget(self.error_label)
        hbl_error.addWidget(self.error_label_text)

        # Create Calculate and Cancel buttons
        self.calculateButton = QPushButton("Set")
        self.calculateButton.clicked.connect(self.calculate_callback)
        self.calculateButton.setDefault(True)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel_callback)

        hb_buttons = QHBoxLayout()
        hb_buttons.addStretch(1)
        hb_buttons.addWidget(self.cancelButton)
        hb_buttons.addWidget(self.calculateButton)

        # Add calculation and buttons to popup box
        vbl = QVBoxLayout()
        vbl.addLayout(hb_desc)
        vbl.addLayout(hb_wavelengthunits)
        vbl.addLayout(hb_redshift)
        vbl.addLayout(hb_wavelengthdisplay)
        vbl.addLayout(hbl_error)
        vbl.addLayout(hb_buttons)

        self.setLayout(vbl)
        self.setMaximumWidth(700)
        self.show()

        # Fire the callback to set the default values for everything
        self._region_selection_change(0)

    def _region_selection_change(self, index):
        """
        Callback for a change on the region selection combo box.

        :param newvalue:
        :return:
        """

        newvalue = self.region_combobox.currentText()

        # First, let's see if this is one of the custom options
        if 'Custom' in newvalue and 'Wavelength' in newvalue:
            # Custom Wavelengths
            self.hide_start_end(False)
            self.start_label.setText("Start Wavelength:")
            self.end_label.setText("End Wavelength:")

        elif 'Custom' in newvalue and 'Indices' in newvalue:
            # Custom indices
            self.hide_start_end(False)
            self.start_label.setText("Start Index:")
            self.end_label.setText("End Index:")

        else:
            # Region defined in specviz
            self.hide_start_end(True)

            # We are going to store the start and end wavelengths in the text boxes even though
            # they are hidden. This way we can use the text boxes later as a hidden storage container.
            # TODO: Should probably save the ROIs so the start and end values are more accurate.
            regex = r"-?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?"
            floating = re.findall(regex, newvalue)
            self.start_text.setText(floating[0])
            self.end_text.setText(floating[1])

        # Let's update the text on the widget
        if 'Custom' in newvalue:
            self.widget_desc.setText(self._general_description + "\n\n" + self._custom_description)
        else:
            self.widget_desc.setText(self._general_description)

    def hide_start_end(self, dohide):
        """
        Show or hide the start and end indices depending if the region
        is defined from the specviz plot OR if we are using custom limits.

        :param dohide:
        :return:
        """
        if dohide:
            self.start_label.hide()
            self.start_text.hide()
            self.end_label.hide()
            self.end_text.hide()
        else:
            self.start_label.show()
            self.start_text.show()
            self.end_label.show()
            self.end_text.show()

    def calculate_callback(self):
        """
        Callback for when they hit calculate
        :return:
        """

        # Grab the values of interest
        data_name = self.data_combobox.currentText()
        start_value = self.start_text.text().strip()
        end_value = self.end_text.text().strip()

        self.error_label_text.setText(' ')
        self.error_label_text.setStyleSheet("color: rgba(255, 0, 0, 128)")

        # Sanity checks first
        if not start_value and not end_value:
            self.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.error_label_text.setText('Must set at least one of start or end value')
            return

        wavelengths = np.array(self.parent._wavelengths)

        # If indicies, get them and check to see if the inputs are good.
        if 'Indices' in self.region_combobox.currentText():
            if len(start_value) == 0:
                start_index = 0
            else:
                try:
                    start_index = int(start_value)
                except ValueError as e:
                    self.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                    self.error_label_text.setText('Start value must be an integer')
                    return

                if start_index < 0:
                    start_index = 0

            if len(end_value) == 0:
                end_index = len(wavelengths)-1
            else:
                try:
                    end_index = int(end_value)
                except ValueError as e:
                    self.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                    self.error_label_text.setText('End value must be an integer')
                    return

                if end_index > len(wavelengths) - 1:
                    end_index = len(wavelengths) - 1
        else:
            # Wavelength inputs
            if len(start_value) == 0:
                start_index = 0
            else:
                # convert wavelength to float value
                try:
                    start_value = float(start_value)
                except ValueError as e:
                    self.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                    self.error_label_text.setText('Start value must be a floating point number')
                    return

                # Look up index
                start_index = np.argsort(np.abs(wavelengths - start_value))[0]

            if len(end_value) == 0:
                end_index = len(wavelengths)-1

            else:
                # convert wavelength to float value
                try:
                    end_value = float(end_value)
                except ValueError as e:
                    self.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                    self.error_label_text.setText('End value must be a floating point number')
                    return

                # Look up index
                end_index = np.argsort(np.abs(wavelengths - end_value))[0]

        # Check to make sure at least one of start or end is within the range of the wavelengths.
        if (start_index < 0 and end_index < 0) or (start_index > len(wavelengths) and end_index > len(wavelengths)):
            self.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.error_label_text.setText('Can not have both start and end outside of the wavelength range.')
            return

        if start_index > end_index:
            self.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.error_label_text.setText('Start value must be less than end value')
            return


        # Check to see if the wavelength (indices) are the same.
        if start_index == end_index:
            self.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.error_label_text.setText('Can not have both start and end wavelengths be the same.')
            return

        # Set the start and end values in the text boxes -- in case they enter one way out of range then
        # we'll fix it.
        ts = start_index if 'Indices' in self.region_combobox.currentText() else wavelengths[start_index]
        self.start_text.setText('{}'.format(ts))

        te = end_index if 'Indices' in self.region_combobox.currentText() else wavelengths[end_index]
        self.end_text.setText('{}'.format(te))


        data_name = self.data_combobox.currentText()
        operation = self.operation_combobox.currentText()

        # Do calculation if we got this far
        wavelengths, new_component = collapse_cube(self.data[data_name], data_name, self.data.coords.wcs,
                                             operation, start_index, end_index)

        # Get the start and end wavelengths from the newly created spectral cube and use for labeling the cube.
        # Convert to the current units.
        start_wavelength = wavelengths[0].to(self.parent._units_controller._new_units)
        end_wavelength = wavelengths[-1].to(self.parent._units_controller._new_units)

        label = '{}-collapse-{} ({:0.3}, {:0.3})'.format(data_name, operation,
                                                         start_wavelength,
                                                         end_wavelength)

        # Apply sigma clipping
        sigma = self.sigma_text.text().strip()

        if len(sigma) > 0:
            try:
                sigma = float(sigma)
            except ValueError as e:
                self.sigma_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                self.error_label_text.setText('If sigma set, it must be a floating point number')
                return

            sigma_lower = self.sigma_lower_text.text().strip()
            if len(sigma_lower) > 0:
                try:
                    sigma_lower = float(sigma_lower)
                except ValueError as e:
                    self.sigma_lower_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                    self.error_label_text.setText('If sigma lower set, it must be a floating point number')
                    return
            else:
                sigma_lower = None

            sigma_upper = self.sigma_upper_text.text().strip()
            if len(sigma_upper) > 0:
                try:
                    sigma_upper = float(sigma_upper)
                except ValueError as e:
                    self.sigma_upper_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                    self.error_label_text.setText('If sigma upper set, it must be a floating point number')
                    return
            else:
                sigma_upper = None

            sigma_iters = self.sigma_iters_text.text().strip()
            if len(sigma_iters) > 0:
                try:
                    sigma_iters = float(sigma_iters)
                except ValueError as e:
                    self.sigma_iters_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                    self.error_label_text.setText('If sigma iters set, it must be a floating point number')
                    return
            else:
                sigma_iters = None

            new_component = sigma_clip(new_component, sigma=sigma, sigma_lower=sigma_lower,
                                                     sigma_upper=sigma_upper, iters=sigma_iters)

            # Add to label so it is clear which overlay/component is which
            if sigma:
                label += ' sigma={}'.format(sigma)

            if sigma_lower:
                label += ' sigma_lower={}'.format(sigma_lower)

            if sigma_upper:
                label += ' sigma_upper={}'.format(sigma_upper)

            if sigma_iters:
                label += ' sigma_iters={}'.format(sigma_iters)

        # Add new overlay/component to cubeviz
        self.parent.add_overlay(new_component, label)

        self.close()

        # Show new dialog
        self.final_dialog(label)

    def final_dialog(self, label):
        """
        Final dialog that to show where the calculated collapsed cube was put.

        :param label:
        :return:
        """

        final_dialog = QDialog()

        # Create data component label and input box
        widget_desc = QLabel('The collapsed cube was added as an overlay with label "{}"'.format(label))
        widget_desc.setWordWrap(True)
        widget_desc.setFixedWidth(350)
        widget_desc.setAlignment((Qt.AlignLeft | Qt.AlignTop))

        hb_desc = QHBoxLayout()
        hb_desc.addWidget(widget_desc)

        # Create Ok button
        okButton = QPushButton("Ok")
        okButton.clicked.connect(lambda: final_dialog.close())
        okButton.setDefault(True)

        hb_buttons = QHBoxLayout()
        hb_buttons.addStretch(1)
        hb_buttons.addWidget(okButton)

        # Add description and buttons to popup box
        vbl = QVBoxLayout()
        vbl.addLayout(hb_desc)
        vbl.addLayout(hb_buttons)

        final_dialog.setLayout(vbl)
        final_dialog.setMaximumWidth(400)
        final_dialog.show()

    def cancel_callback(self, caller=0):
        """
        Cancel callback when the person hits the cancel button

        :param caller:
        :return:
        """
        self.close()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.cancel_callback()


def collapse_cube(data_component, data_name, wcs, operation, start_index, end_index):
    """

    :param data_component:  Component from the data object
    :param wcs:
    :param operation:
    :param start:
    :param end:
    :return:
    """

    # Grab spectral-cube
    import spectral_cube

    # Create a spectral cube instance
    cube = spectral_cube.SpectralCube(data_component, wcs=wcs)

    # Do collapsing of the cube
    sub_cube = cube[start_index:end_index]
    calculated = sub_cube.apply_numpy_function(operations[operation], axis=0)

    wavelengths = sub_cube.spectral_axis

    # Send collapsed cube back to cubeviz
    return wavelengths, calculated
