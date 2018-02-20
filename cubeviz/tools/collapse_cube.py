from __future__ import absolute_import, division, print_function

from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy.QtWidgets import (
    QDialog, QApplication, QPushButton,
    QLabel, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox
)


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
        self.operation_combobox.addItems(['mean', 'median', 'std'])
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

        data_name = self.data_combobox.currentText()

        # Do calculation if we bggot this

        # self.parent.add_overlay(cube_moment.value, label)

        self.close()

    def cancel_callback(self, caller=0):
        """
        Cancel callback when the person hits the cancel button

        :param caller:
        :return:
        """
        self.close()


def collapse_cube(data_component, wcs, operation, start, end):
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
    print('created spectral cube {}'.format(spectral_cube))

    # Do collapsing of the cube
    # cube_moment = cube.moment(order=order, axis=0)
    #
    # label = '{}-moment-{}'.format(data_name, order)
    # self.parent.add_overlay(cube_moment.value, label)

    # Send collapsed cube back to cubeviz
    #return cube_moment, label