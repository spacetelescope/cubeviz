from __future__ import absolute_import, division, print_function

from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy.QtWidgets import (
    QDialog, QApplication, QPushButton,
    QLabel, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox
)

import numpy as np

# The operations we understand
operations = {
    'mean': np.mean,
    'median': np.median,
    'std': np.std
}

class CollapseCube(QDialog):
    def __init__(self, data, data_collection=[], allow_preview=False, parent=None):
        super(CollapseCube,self).__init__(parent)

        # Get the data_components (e.g., FLUX, DQ, ERROR etc)
        # Using list comprehension to keep the order of the component_ids
        self.data_components = [str(x).strip() for x in data.component_ids() if not x in data.coordinate_components]

        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.title = "Cube Collapse"
        self.data = data
        self.data_collection = data_collection
        self.parent = parent

        self.currentAxes = None
        self.currentKernel = None

        print('Going to call createUI')
        self.createUI()

    def createUI(self):
        """
        Create the popup box with the calculation input area and buttons.

        :return:
        """
        print("In createUI")

        boldFont = QtGui.QFont()
        boldFont.setBold(True)

        # Create data component label and input box
        self.data_label = QLabel("Data:")
        self.data_label.setFixedWidth(100)
        self.data_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.data_label.setFont(boldFont)

        self.data_combobox = QComboBox()
        self.data_combobox.addItems([str(x).strip() for x in self.data.component_ids() if not x in self.data.coordinate_components])
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

        # Create calculation label and input box
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

        print('here')

        # Add calculation and buttons to popup box
        vbl = QVBoxLayout()
        vbl.addLayout(hb_data)
        vbl.addLayout(hb_operation)
        vbl.addLayout(hb_start)
        vbl.addLayout(hb_end)
        vbl.addLayout(hbl_error)
        vbl.addLayout(hb_buttons)

        self.setLayout(vbl)
        self.setMaximumWidth(700)
        self.show()

    def calculate_callback(self):
        """
        Callback for when they hit calculate
        :return:
        """

        # Grab the values of interest
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

        end_value = int(end_value)

        data_name = self.data_combobox.currentText()
        operation = self.operation_combobox.currentText()

        # Do calculation if we got this far
        new_component, label = collapse_cube(self.data[data_name], data_name, self.data.coords.wcs,
                                             operation, start_value, end_value)

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

    label = '{}-collapse-{}'.format(data_name, operation)

    # Send collapsed cube back to cubeviz
    return calculated, label