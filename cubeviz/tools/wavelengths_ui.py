from __future__ import absolute_import, division, print_function

from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy.QtWidgets import (
    QDialog, QApplication, QPushButton,
    QLabel, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox
)

from astropy.stats import sigma_clip
from glue.utils.qt import load_ui

import numpy as np
import re
import os

from ..controls.wavelengths import REST_WAVELENGTH_TEXT, OBS_WAVELENGTH_TEXT

class WavelengthUI(QDialog):
    def __init__(self, wavelength_controller, parent=None):
        super(WavelengthUI,self).__init__(parent)

        self.wavelength_controller = wavelength_controller

        # Load the widget from the UI file.
        self.ui = load_ui('wavelength.ui', self,
                          directory=os.path.dirname(__file__))

        # Add the wavelength units to the combo box
        self.ui.wavelengthunits_combobox.addItems(
                self.wavelength_controller.unit_titles)

        current_units = self.wavelength_controller.current_units
        self.ui.wavelengthunits_combobox.setCurrentIndex(
            self.wavelength_controller.units.index(current_units))

        # Add the wavelength display to the combo box
        self.ui.wavelengthdisplay_combobox.addItems(
                [OBS_WAVELENGTH_TEXT, REST_WAVELENGTH_TEXT])

        # Set default values based on what was previously selected
        # This should be before the callbacks just so we don't fire anything
        z = wavelength_controller.redshift_z
        self.ui.wavelengthdisplay_combobox.setCurrentIndex(0 if z == 0 else 1)
        self.ui.redshift_text.setText(str(z))

        # We want to initially disable the redshift part if there
        # is no redshift, then when they switch to "Rest Wavelength"
        # these will be enabled.
        self.ui.redshift_label.setDisabled(z == 0)
        self.ui.redshift_text.setDisabled(z == 0)

        # Setup the callbacks on the UI
        self.ui.wavelengthdisplay_combobox.currentIndexChanged.connect(
                self._wavelengthdisplay_selection_change)
        self.ui.calculate_button.clicked.connect(self._calculate_callback)
        self.ui.cancel_button.clicked.connect(self._cancel_callback)

        self.ui.show()

    def do_calculation(self, wavelength_redshift, wavelength_units):
        """
        Actual calculate function so that we can use this in the
        testing scripts as well.

        :param wavelength_redshift:  z-value
        :param wavelength_units: text representation of the units
        :return: nuttin
        """
        self.wavelength_controller.update_units(wavelength_units)
        self.wavelength_controller.update_redshift(wavelength_redshift)

    def _calculate_callback(self):

        # Reset the errors
        self.ui.error_text.setText(' ')
        self.ui.error_text.setStyleSheet("color: rgba(0, 0, 0, 128)")
        self.ui.redshift_label.setStyleSheet("color: rgba(0, 0, 0, 128)")

        # Check the redshift value if we are using the Obs wavelengths
        if REST_WAVELENGTH_TEXT == self.wavelengthdisplay_combobox.currentText():
            redshift = self.ui.redshift_text.text().strip()

            try:
                redshift = float(redshift)
            except Exception as e:
                self.ui.redshift_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                self.ui.error_text.setText('Redshift value {} does not appear to be a number'.format(redshift))
                return
        else:
            redshift = 0.0

        # Get the units based on the index in the units combo box.
        index = self.ui.wavelengthunits_combobox.currentIndex()
        units = self.wavelength_controller.units[index]

        # Do the actual calculation
        self.do_calculation(wavelength_redshift=redshift, wavelength_units=units)

        self.close()

    def _cancel_callback(self, caller=0):
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
        newvalue = self.ui.wavelengthdisplay_combobox.currentText()

        # Hide the redshift stuff if Observed wavelength is selected
        self.ui.redshift_label.setDisabled(newvalue == OBS_WAVELENGTH_TEXT)
        self.ui.redshift_text.setDisabled(newvalue == OBS_WAVELENGTH_TEXT)
