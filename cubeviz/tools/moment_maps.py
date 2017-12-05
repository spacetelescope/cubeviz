from __future__ import absolute_import, division, print_function

import numpy as np
from matplotlib import pyplot as plt

from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy.QtWidgets import (
    QMainWindow, QComboBox, QPushButton,
    QLabel, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit
)


# TODO: In the future, it might be nice to be able to work across data_collection elements

class MomentMapsGUI(QMainWindow):
    def __init__(self, data, overlays, data_collection, parent=None):
        super(MomentMapsGUI, self).__init__(parent)

        # Get the data_components (e.g., FLUX, DQ, ERROR etc)
        # Using list comprehension to keep the order of the component_ids
        self.data_components = [str(x).strip() for x in data.component_ids() if not x in data.coordinate_components]

        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.title = "Arithmetic Calculation"
        self.data = data
        self.overlays = overlays
        self.data_collection = data_collection
        self.parent = parent

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

        # Create calculation label and input box
        self.data_label = QLabel("Data:")
        self.data_label.setFixedWidth(100)
        self.data_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.data_label.setFont(boldFont)

        self.data_combobox = QComboBox()
        self.data_combobox.addItems(["FLUX", "ERROR", "DQ"])
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

        self.wid = QWidget(self)
        self.setCentralWidget(self.wid)
        self.wid.setLayout(vbl)
        self.setMaximumWidth(700)
        self.show()

    def _display_overlay(self, data):
        extent = 0, data.shape[0], 0, data.shape[1]

        aspect = self.parent.left_view._widget.axes.get_aspect()
        im2 = self.parent.left_view._widget.axes.imshow(data,
                                                        origin='lower',
                                                        cmap=plt.cm.hot,
                                                        alpha=.25,
                                                        interpolation='none',
                                                        aspect=aspect,
                                                        extent=extent)
        self.parent.left_view._widget.figure.canvas.draw()

    def calculate_callback(self):
        """
        Callback for when they hit calculate
        :return:
        """
        print('In callback')

        # Determine the data component and order
        order = int(self.order_combobox.currentText())
        data_name = self.data_combobox.currentText()

        print('order, datanme {}, {}'.format(order, data_name))

        # Grab spectral-cube
        import spectral_cube
        cube = spectral_cube.SpectralCube(self.data[data_name], wcs=self.data.coords.wcs)

        # Use the package asteval to do the calculation, we are going to
        # assume here that the lhs of the equals sign is going to be the output named variable

        #try:
        print('Going to calculate...')
        cube_moment = cube.moment(order=order, axis=0)

        print('Going to add component... {}'.format(cube_moment.shape))
        label = '{}-moment-{}'.format(data_name, order)
        self.overlays.add_component(cube_moment.value, label)
        self._display_overlay(cube_moment.value)

        #except Exception as e:
        #    print('Error {}'.format(e))
        #    print(e)

        print('Done and closing')
        self.close()

    def cancel_callback(self, caller=0):
        """
        Cancel callback when the person hits the cancel button

        :param caller:
        :return:
        """
        self.close()
