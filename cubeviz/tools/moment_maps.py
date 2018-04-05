from __future__ import absolute_import, division, print_function

from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy.QtWidgets import (QDialog, QComboBox, QPushButton,
                            QLabel, QWidget, QHBoxLayout, QVBoxLayout)

from .common import add_to_2d_container, show_error_message


# TODO: In the future, it might be nice to be able to work across data_collection elements

class MomentMapsGUI(QDialog):
    def __init__(self, data, data_collection, parent=None):
        super(MomentMapsGUI, self).__init__(parent)

        # Get the data_components (e.g., FLUX, DQ, ERROR etc)
        # Using list comprehension to keep the order of the component_ids
        self.data_components = [str(x).strip() for x in data.component_ids() if not x in data.coordinate_components]

        self.data = data
        self.data_collection = data_collection
        self.parent = parent

        self.label = ''

    def display(self):
        """
        Create the popup box with the calculation input area and buttons.

        :return:
        """
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.setWindowTitle("Create Moment Map")

        boldFont = QtGui.QFont()
        boldFont.setBold(True)

        # Create calculation label and input box
        self.data_label = QLabel("Data:")
        self.data_label.setFixedWidth(100)
        self.data_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.data_label.setFont(boldFont)

        self.data_combobox = QComboBox()
        self.data_combobox.addItems([str(x).strip() for x in self.data.component_ids() if not x in self.data.coordinate_components])
        self.data_combobox.setMinimumWidth(200)

        hbl1 = QHBoxLayout()
        hbl1.addWidget(self.data_label)
        hbl1.addWidget(self.data_combobox)

        # Create calculation label and input box
        self.order_label = QLabel("Order:")
        self.order_label.setFixedWidth(100)
        self.order_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.order_label.setFont(boldFont)

        self.order_combobox = QComboBox()
        self.order_combobox.addItems(["1", "2", "3", "4", "5", "6", "7", "8"])
        self.order_combobox.setMinimumWidth(200)

        hbl2 = QHBoxLayout()
        hbl2.addWidget(self.order_label)
        hbl2.addWidget(self.order_combobox)

        # Create Calculate and Cancel buttons
        self.calculateButton = QPushButton("Calculate")
        self.calculateButton.clicked.connect(self.calculate_callback)
        self.calculateButton.setDefault(True)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel_callback)

        hbl5 = QHBoxLayout()
        hbl5.addStretch(1)
        hbl5.addWidget(self.cancelButton)
        hbl5.addWidget(self.calculateButton)

        # Add calculation and buttons to popup box
        vbl = QVBoxLayout()
        vbl.addLayout(hbl1)
        vbl.addLayout(hbl2)
        vbl.addLayout(hbl5)

        self.setLayout(vbl)
        self.setMaximumWidth(700)
        self.show()

    def do_calculation(self, order, data_name):
        # Grab spectral-cube
        import spectral_cube
        cube = spectral_cube.SpectralCube(self.data[data_name], wcs=self.data.coords.wcs)

        cube_moment = cube.moment(order=order, axis=0)

        self.label = '{}-moment-{}'.format(data_name, order)

        # Add new overlay/component to cubeviz. We add this both to the 2D
        # container Data object and also as an overlay. In future we might be
        # able to use the 2D container Data object for the overlays directly.
        add_to_2d_container(self.parent, self.data, cube_moment.value, self.label)
        self.parent.add_overlay(cube_moment.value, self.label, display_now=False)

    def calculate_callback(self):
        """
        Callback for when they hit calculate
        :return:
        """

        # Determine the data component and order
        order = int(self.order_combobox.currentText())
        data_name = self.data_combobox.currentText()

        try:
            self.do_calculation(order, data_name)
        except Exception as e:
            print('Error: {}'.format(e))
            show_error_message(str(e), 'Moment Map Error', parent=self)

        self.close()

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
