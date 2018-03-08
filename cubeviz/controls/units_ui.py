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
    def __init__(self, wavelength_units, parent=None):
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
        self.widget_desc.setFixedWidth(400)
        self.widget_desc.setAlignment((Qt.AlignLeft | Qt.AlignTop))

        hb_desc = QHBoxLayout()
        hb_desc.addWidget(self.widget_desc)

        # Create wavelength units component label and input box
        self.wavelengthunits_label = QLabel("Wavelength Units:")
        self.wavelengthunits_label.setFixedWidth(120)
        self.wavelengthunits_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.wavelengthunits_label.setFont(boldFont)

        self.wavelengthunits_combobox = QComboBox()
        self.wavelengthunits_combobox.addItems(self.wavelength_units)
        self.wavelengthunits_combobox.setMinimumWidth(200)

        hb_wavelengthunits = QHBoxLayout()
        hb_wavelengthunits.addWidget(self.wavelengthunits_label)
        hb_wavelengthunits.addWidget(self.wavelengthunits_combobox)

        # Create wavelength units component label and input box
        self.wavelengthdisplay_label = QLabel("Wavelength Display:")
        self.wavelengthdisplay_label.setFixedWidth(120)
        self.wavelengthdisplay_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.wavelengthdisplay_label.setFont(boldFont)

        self.wavelengthdisplay_combobox = QComboBox()
        self.wavelengthdisplay_combobox.addItems(['Obs Wavelengths', 'Rest Wavelengths'])
        self.wavelengthdisplay_combobox.setMinimumWidth(200)
        self.wavelengthdisplay_combobox.currentIndexChanged.connect(self._wavelengthdisplay_selection_change)

        hb_wavelengthdisplay = QHBoxLayout()
        hb_wavelengthdisplay.addWidget(self.wavelengthdisplay_label)
        hb_wavelengthdisplay.addWidget(self.wavelengthdisplay_combobox)

        # Create redshift label and input box
        self.redshift_label = QLabel("RedShift:")
        self.redshift_label.setFixedWidth(120)
        self.redshift_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.redshift_label.setFont(boldFont)

        self.redshift_combobox = QLineEdit()
        self.redshift_combobox.setMinimumWidth(200)

        hb_redshift = QHBoxLayout()
        hb_redshift.addWidget(self.redshift_label)
        hb_redshift.addWidget(self.redshift_combobox)

        # Going to hide these initially, when the "Rest Wavelengths is selected then
        # we will show them.
        self.redshift_label.hide()
        self.redshift_combobox.hide()

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
        vbl.addLayout(hb_wavelengthdisplay)
        vbl.addLayout(hb_redshift)
        vbl.addLayout(hbl_error)
        vbl.addLayout(hb_buttons)

        self.setLayout(vbl)
        self.setMaximumWidth(700)
        self.show()

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

    def _wavelengthdisplay_selection_change(self, index):
        """
        Callback for a change on the region selection combo box.

        :param newvalue:
        :return:
        """
        newvalue = self.wavelengthdisplay_combobox.currentText()

        # Hide the redshift stuff if Observed wavelength is selected
        if 'Obs' in newvalue:
            self.redshift_label.hide()
            self.redshift_combobox.hide()

        elif 'Rest' in newvalue:
            self.redshift_label.show()
            self.redshift_combobox.show()
