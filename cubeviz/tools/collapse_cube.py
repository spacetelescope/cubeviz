from __future__ import absolute_import, division, print_function

from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy.QtWidgets import (
    QDialog, QApplication, QPushButton,
    QLabel, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox
)

import numpy as np
import re

# The operations we understand
operations = {
    'Sum': np.sum,
    'Mean': np.mean,
    'Median': np.median,
    'Standard Deviation': np.std,
    'Maximum': np.max,
    'Minimum': np.min,
    'Sum (ignore NaNs)': np.nansum,
    'Mean (ignore NaNs)': np.nanmean,
    'Median (ignore NaNs)': np.nanmedian,
    'Standard Deviation (ignore NaNs)': np.nanstd,
    'Maximum (ignore NaNs)': np.nanmax,
    'Minimum (ignore NaNs)': np.nanmin
}

class CollapseCube(QDialog):
    def __init__(self, data, data_collection=[], allow_preview=False, parent=None):
        super(CollapseCube,self).__init__(parent)

        self.setWindowTitle("Collapse Cube Along Spectral Axis")

        # Get the data_components (e.g., FLUX, DQ, ERROR etc)
        # Using list comprehension to keep the order of the component_ids
        self.data_components = [str(x).strip() for x in data.component_ids() if not x in data.coordinate_components]

        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.title = "Cube Collapse"
        self.data = data
        self.data_collection = data_collection
        self.parent = parent

        self._general_description = "Collapse the data cube over the spectral range based on the mathematical operation."
        self._custom_description = "To use the spectral viewer to define a region to collapse over, cancel this, create an ROI and then select this Collapse Cube again."

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

        # Create data component label and input box
        self.data_label = QLabel("Data:")
        self.data_label.setFixedWidth(100)
        self.data_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.data_label.setFont(boldFont)

        self.data_combobox = QComboBox()
        self.data_combobox.addItems([str(x).strip() for x in self.data.component_ids()
                                     if not x in self.data.coordinate_components])
        self.data_combobox.setMinimumWidth(200)

        hb_data = QHBoxLayout()
        hb_data.addWidget(self.data_label)
        hb_data.addWidget(self.data_combobox)

        # Create operation label and input box
        self.operation_label = QLabel("Operation:")
        self.operation_label.setFixedWidth(100)
        self.operation_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.operation_label.setFont(boldFont)

        self.operation_combobox = QComboBox()
        self.operation_combobox.addItems(operations.keys())
        self.operation_combobox.setMinimumWidth(200)

        hb_operation = QHBoxLayout()
        hb_operation.addWidget(self.operation_label)
        hb_operation.addWidget(self.operation_combobox)

        # Create region label and input box
        self.region_label = QLabel("region:")
        self.region_label.setFixedWidth(100)
        self.region_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.region_label.setFont(boldFont)

        self.region_combobox = QComboBox()

        # Get the Specviz regions and add them in to the Combo box
        for roi in self.parent.specviz._widget.roi_bounds:
            self.region_combobox.addItem("Specviz ROI ({:.3}, {:.3})".format(roi[0], roi[1]))

        self.region_combobox.addItems(["Custom (Wavelengths)", "Custom (Indices)"])
        self.region_combobox.setMinimumWidth(200)
        self.region_combobox.currentIndexChanged.connect(self._region_selection_change)

        hb_region = QHBoxLayout()
        hb_region.addWidget(self.region_label)
        hb_region.addWidget(self.region_combobox)

        # Create error label
        self.error_label = QLabel("")
        self.error_label.setFixedWidth(100)

        self.error_label_text = QLabel("")
        self.error_label_text.setMinimumWidth(200)
        self.error_label_text.setAlignment((Qt.AlignLeft | Qt.AlignTop))

        hbl_error = QHBoxLayout()
        hbl_error.addWidget(self.error_label)
        hbl_error.addWidget(self.error_label_text)

        # Create start label and input box
        self.start_label = QLabel("Start:")
        self.start_label.setFixedWidth(100)
        self.start_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.start_label.setFont(boldFont)

        self.start_text = QLineEdit()
        self.start_text.setMinimumWidth(200)
        self.start_text.setAlignment((Qt.AlignLeft | Qt.AlignTop))

        hb_start = QHBoxLayout()
        hb_start.addWidget(self.start_label)
        hb_start.addWidget(self.start_text)

        # Create end label and input box
        self.end_label = QLabel("End:")
        self.end_label.setFixedWidth(100)
        self.end_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.end_label.setFont(boldFont)

        self.end_text = QLineEdit()
        self.end_text.setMinimumWidth(200)
        self.end_text.setAlignment((Qt.AlignLeft | Qt.AlignTop))

        hb_end = QHBoxLayout()
        hb_end.addWidget(self.end_label)
        hb_end.addWidget(self.end_text)

        # Create Calculate and Cancel buttons
        self.calculateButton = QPushButton("Calculate")
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
        vbl.addLayout(hb_data)
        vbl.addLayout(hb_operation)
        vbl.addLayout(hb_region)
        vbl.addLayout(hb_start)
        vbl.addLayout(hb_end)
        vbl.addLayout(hbl_error)
        vbl.addLayout(hb_buttons)

        # Fire the callback to set the default values for everything
        self._region_selection_change(0)

        self.setLayout(vbl)
        self.setMaximumWidth(700)
        self.show()

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
        start_value = float(self.start_text.text().strip())
        end_value = float(self.end_text.text().strip())

        # Convert wavelengths to indices IF the region combo box is not the Indices selection
        if not 'Indices' in self.region_combobox.currentText():
            wavelengths = np.array(self.parent._wavelengths)
            start_value = np.argsort(np.abs(wavelengths - start_value))[0]
            end_value = np.argsort(np.abs(wavelengths - end_value))[0]

        self.error_label_text.setText(' ')
        self.error_label_text.setStyleSheet("color: rgba(255, 0, 0, 128)")

        # Sanity checks first
        if not start_value and not end_value:
            self.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.error_label_text.setText('Must set at least one of start or end value')
            return

        if start_value and end_value and start_value > end_value:
            self.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.error_label_text.setText('Start value must be less than end value')
            return

        # Set the start and end values if they are not set.
        if not start_value:
            start_value = 0

        if not end_value:
            end_value = self.data[data_name].shape[0]

        try:
            start_value = int(start_value)
        except TypeError as e:
            self.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.error_label_text.setText('Start value, {}, does not appear to be an number'.format(start_value))
            return

        try:
            end_value = int(end_value)
        except TypeError as e:
            self.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.error_label_text.setText('End value, {}, does not appear to be an number'.format(end_value))
            return

        data_name = self.data_combobox.currentText()
        operation = self.operation_combobox.currentText()

        # Do calculation if we got this far
        wavelengths, new_component = collapse_cube(self.data[data_name], data_name, self.data.coords.wcs,
                                             operation, start_value, end_value)

        # Get the start and end wavelengths from the newly created spectral cube and use for labeling the cube.
        # Convert to the current units.
        start_wavelength = wavelengths[0].to(self.parent._units_controller._new_units)
        end_wavelength = wavelengths[-1].to(self.parent._units_controller._new_units)

        label = '{}-collapse-{} ({:0.3}, {:0.3})'.format(data_name, operation,
                                                         start_wavelength,
                                                         end_wavelength)

        self.parent.add_overlay(new_component, label)

        self.close()

    def cancel_callback(self, caller=0):
        """
        Cancel callback when the person hits the cancel button

        :param caller:
        :return:
        """
        self.close()


def collapse_cube(data_component, data_name, wcs, operation, start_value, end_value):
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
    sub_cube = cube[start_value:end_value]
    calculated = sub_cube.apply_numpy_function(operations[operation], axis=0)

    wavelengths = sub_cube.spectral_axis

    # Send collapsed cube back to cubeviz
    return wavelengths, calculated