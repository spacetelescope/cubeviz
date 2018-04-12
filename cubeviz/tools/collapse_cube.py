from __future__ import absolute_import, division, print_function

import re
import os
from collections import OrderedDict
import numpy as np

from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy.QtWidgets import (QDialog, QApplication, QPushButton, QLabel, QWidget,
                            QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox)
from glue.utils.qt import load_ui

from astropy.stats import sigma_clip

from .common import add_to_2d_container, show_error_message

import logging
logging.basicConfig(format='%(levelname)-6s: %(name)-10s %(asctime)-15s  %(message)s')
log = logging.getLogger("CollapseCube")
log.setLevel(logging.WARNING)

# The operations we understand
operations = OrderedDict([
    ('Sum', np.sum),
    ('Mean', np.mean),
    ('Median', np.median),
    ('Standard Deviation', np.std),
    ('Maximum', np.max),
    ('Minimum', np.min),
    ('Sum (ignore NaNs)', np.nansum),
    ('Mean (ignore NaNs)', np.nanmean),
    ('Median (ignore NaNs)', np.nanmedian),
    ('Standard Deviation (ignore NaNs)', np.nanstd),
    ('Maximum (ignore NaNs)', np.nanmax),
    ('Minimum (ignore NaNs)', np.nanmin)
])

class CollapseCube(QDialog):
    def __init__(self, wavelengths, wavelength_units, data, data_collection=[],
                 allow_preview=False, parent=None):

        super(CollapseCube,self).__init__(parent)

        self.setWindowTitle("Collapse Cube Along Spectral Axis")

        # Get the data_components (e.g., FLUX, DQ, ERROR etc)
        # Using list comprehension to keep the order of the component_ids
        self.data_components = [str(x).strip() for x in data.component_ids() if not x in data.coordinate_components]

        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.title = "Cube Collapse"

        self.wavelengths = wavelengths
        self.wavelength_units = wavelength_units
        self.data = data
        self.data_collection = data_collection
        self.parent = parent

        self._general_description = "Collapse the data cube over the spectral range based on the mathematical operation.  The nearest index or wavelength will be chosen if a specified number is out of bounds"
        self._custom_description = "To use the spectral viewer to define a region to collapse over, cancel this, create an ROI and then select this Collapse Cube again."

        self._extra_message = ''

        self.currentAxes = None
        self.currentKernel = None

        self.createUI()

    def createUI(self):
        """
        Create the popup box with the calculation input area and buttons.

        :return:
        """
        # Load the widget from the UI file.
        self.ui = load_ui('collapse.ui', self,
                          directory=os.path.dirname(__file__))

        self.ui.data_combobox.addItems([str(x).strip() for x in self.data.component_ids()
                                      if not x in self.data.coordinate_components])
        self.ui.operation_combobox.addItems(operations.keys())

        # Fill spatial region combobox
        spatial_regions = ['Image'] + [x.label for x in self.data.subsets]
        self.ui.spatial_region_combobox.addItems(spatial_regions)

        # Get the Specviz regions and add them in to the Combo box
        for roi in self.parent.specviz._widget.roi_bounds:
            self.ui.region_combobox.addItem("Specviz ROI ({:.4e}, {:.4e})".format(roi[0], roi[1]))

        self.ui.region_combobox.addItems(["Custom (Wavelengths)", "Custom (Indices)"])
        self.ui.region_combobox.setMinimumWidth(200)
        self.ui.region_combobox.currentIndexChanged.connect(self._region_selection_change)

        self.ui.desc_label.setText(self._general_description)

        # Set defaults for wavelengths
        indthird = len(self.wavelengths) // 3
        self.ui.start_input.setText('{:.4e}'.format(self.wavelengths[indthird]))
        self.ui.end_input.setText('{:.4e}'.format(self.wavelengths[2*indthird]))

        # Hide the error box... for now.
        self.ui.error_label.setVisible(False)

        # Setup call back for the Advanced Sigma Checkbox
        self.ui.region_combobox.currentIndexChanged.connect(self._region_combobox_callback)

        # Setup call back for the Advanced Sigma Checkbox
        self.ui.sigma_combobox.currentIndexChanged.connect(self._sigma_combobox_callback)

        # Setup the call back for the buttons
        self.ui.calculate_button.clicked.connect(self.calculate_callback)
        self.ui.cancel_button.clicked.connect(self.cancel_callback)

        self.ui.show()

        # Fire the callback to set the default values for everything
        self._sigma_combobox_callback(0)
        self._region_selection_change(0)

    def _region_combobox_callback(self, index):
        log.debug('_region_combobox_callback with index {}'.format(index))

        combo_text = self.ui.region_combobox.currentText()

        if 'Custom (Wavelengths)' == combo_text:  # convert to custom wavelengths
            # try to convert the text boxes to wavelengths
            start = self.ui.start_input.text().strip()
            log.debug('    start = {}'.format(start))
            try:
                if float(start).is_integer():
                    start = int(start)
                    self.ui.start_input.setText('{:.4e}'.format(self.wavelengths[int(start)]))
            except:
                self.ui.start_input.setText('')

            # try to convert the text boxes to wavelengths
            end = self.ui.end_input.text().strip()
            log.debug('    end = {}'.format(end))
            try:
                if float(end).is_integer():
                    end = int(end)
                    self.ui.end_input.setText('{:.4e}'.format(self.wavelengths[int(end)]))
            except:
                self.ui.end_input.setText('')

        elif 'Custom (Indices)' == combo_text:  # convert to custom indices
            # try to convert the text boxes to indices
            start = self.ui.start_input.text().strip()
            log.debug('    start = {}'.format(start))
            try:
                ind = np.argsort(abs(float(start) - self.wavelengths))[0]
                self.ui.start_input.setText('{}'.format(ind))
            except:
                self.ui.start_input.setText('')

            # try to convert the text boxes to wavelengths
            end = self.ui.end_input.text().strip()
            log.debug('    end = {}'.format(end))
            try:
                ind = np.argsort(abs(float(end) - self.wavelengths))[0]
                self.ui.end_input.setText('{}'.format(ind))
            except:
                self.ui.end_input.setText('')

    def _sigma_combobox_callback(self, index):

        # Show / Hide simple sigma options
        self.ui.simple_sigma_label.setVisible(index == 1)
        self.ui.simple_sigma_description.setVisible(index == 1)
        self.ui.simple_sigma_input.setVisible(index == 1)

        # Show / Hide advanced sigma options
        self.ui.advanced_sigma_label.setVisible(index == 2)
        self.ui.advanced_sigma_description.setVisible(index == 2)
        self.ui.advanced_sigma_lower_label.setVisible(index == 2)
        self.ui.advanced_sigma_upper_label.setVisible(index == 2)
        self.ui.advanced_sigma_iters_label.setVisible(index == 2)

        self.ui.advanced_sigma_input.setVisible(index == 2)
        self.ui.advanced_sigma_lower_input.setVisible(index == 2)
        self.ui.advanced_sigma_upper_input.setVisible(index == 2)
        self.ui.advanced_sigma_iters_input.setVisible(index == 2)

    def _region_selection_change(self, index):
        """
        Callback for a change on the region selection combo box.

        :param newvalue:
        :return:
        """

        newvalue = self.region_combobox.currentText()
        indthird = len(self.wavelengths) // 3

        # First, let's see if this is one of the custom options
        if 'Custom' in newvalue and 'Wavelength' in newvalue:
            # Custom Wavelengths
            self.hide_start_end(False)
            self.ui.start_label.setText("Start Wavelength:")
            self.ui.end_label.setText("End Wavelength:")

            self.ui.start_example_label.setText('(e.g., {:.4e})'.format(self.wavelengths[indthird]))
            self.ui.end_example_label.setText('(e.g., {:.4e})'.format(self.wavelengths[2*indthird]))

        elif 'Custom' in newvalue and 'Indices' in newvalue:
            # Custom indices
            self.hide_start_end(False)
            self.ui.start_label.setText("Start Index:")
            self.ui.end_label.setText("End Index:")

            self.ui.start_example_label.setText('(e.g., {})'.format(indthird))
            self.ui.end_example_label.setText('(e.g., {})'.format(2*indthird))

        else:
            # Region defined in specviz
            self.hide_start_end(True)

            # We are going to store the start and end wavelengths in the text boxes even though
            # they are hidden. This way we can use the text boxes later as a hidden storage container.
            # TODO: Should probably save the ROIs so the start and end values are more accurate.
            regex = r"-?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?"
            floating = re.findall(regex, newvalue)
            self.ui.start_input.setText(floating[0])
            self.ui.end_input.setText(floating[1])

        # Let's update the text on the widget
        if 'Custom' in newvalue:
            self.ui.desc_label.setText(self._general_description + '\n' + self._custom_description)
        else:
            self.ui.desc_label.setText(self._general_description)

    def hide_start_end(self, dohide):
        """
        Show or hide the start and end indices depending if the region
        is defined from the specviz plot OR if we are using custom limits.

        :param dohide:
        :return:
        """
        self.ui.start_label.setEnabled(not dohide)
        self.ui.start_example_label.setEnabled(not dohide)
        self.ui.start_input.setEnabled(not dohide)
        self.ui.end_label.setEnabled(not dohide)
        self.ui.end_example_label.setEnabled(not dohide)
        self.ui.end_input.setEnabled(not dohide)

    def _calculate_callback_wavelength_checks(self, start_wavelength, end_wavelength):

        log.debug('_calculate_callback_wavelength_checks with start {} and end {}'.format(
            start_wavelength, end_wavelength))

        if len(start_wavelength) == 0:
            start_wavelength = self.wavelengths[0]
            self.ui.start_input.setText('{:.4e}'.format(start_wavelength))
            self._extra_message += ' Start wavelength not set so used the first.'

        if len(end_wavelength) == 0:
            end_wavelength = self.wavelengths[-1]
            self.ui.end_input.setText('{:.4e}'.format(end_wavelength))
            self._extra_message += ' End wavelength not set so used the last.'

        try:
            start_wavelength = float(start_wavelength)
        except:
            self.ui.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Start wavelength is not a floating point number.')
            self.ui.error_label.setVisible(True)

            return None, None

        try:
            end_wavelength = float(end_wavelength)
        except:
            self.ui.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('End wavelength is not a floating point number.')
            self.ui.error_label.setVisible(True)

            return None, None

        if start_wavelength < self.wavelengths[0]:
            self.ui.error_label.setText('Start wavelength is out of range, setting to end point.')
            self.ui.error_label.setVisible(True)
            self._extra_message += ' Start wavelength too low, using the first wavelength.'

            start_wavelength = self.wavelengths[0]

        if start_wavelength > self.wavelengths[-1]:
            self.ui.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Start wavelength is out of range.')
            self.ui.error_label.setVisible(True)
            return None, None

        if end_wavelength < start_wavelength:
            self.ui.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Start wavelength must be less than the end wavelength.')
            self.ui.error_label.setVisible(True)
            return None, None

        if end_wavelength > self.wavelengths[-1]:
            self.ui.error_label.setText('End wavelength is out of range, setting to end point.')
            self.ui.error_label.setVisible(True)
            self._extra_message += ' End wavelength too high, using the last wavelength.'

            end_wavelength = self.wavelengths[-1]

        if end_wavelength < self.wavelengths[0]:
            self.ui.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('End wavelength is out of range.')
            self.ui.error_label.setVisible(True)

            end_wavelength = None

        start_index = np.argsort(abs(self.wavelengths - start_wavelength))[0]
        end_index = np.argsort(abs(self.wavelengths - end_wavelength))[0]

        log.debug('  returning with start_index {} and end_index {}'.format(
            start_index, end_index))

        return start_index, end_index

    def _calculate_callback_index_checks(self, start_index, end_index):

        log.debug('_calculate_callback_index_checks with start {} and end {}'.format(
            start_index, end_index))

        if len(start_index) == 0:
            start_index = 0
            self.ui.start_input.setText('{}'.format(start_index))
            self._extra_message += ' Start wavelength not set so used the first.'

        if len(end_index) == 0:
            end_index = len(self.wavelengths) - 1
            self.ui.end_input.setText('{}'.format(end_index))
            self._extra_message += ' End wavelength not set so used the last.'

        try:
            start_index = int(start_index)
        except:
            self.ui.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Start index is not an integer.')
            self.ui.error_label.setVisible(True)

            start_index = None

        try:
            end_index = int(end_index)
        except:
            self.ui.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('End index is not an integer.')
            self.ui.error_label.setVisible(True)

            end_index = None

        if start_index < 0:
            self.ui.error_label.setText('Start index is out of range, setting to end point.')
            self.ui.error_label.setVisible(True)
            self._extra_message += ' Start wavelength too low, using the first wavelength.'

            start_index = 0

        if start_index > len(self.wavelengths):
            self.ui.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Start index is out of range.')
            self.ui.error_label.setVisible(True)

            start_index = None

        if end_index < start_index:
            self.ui.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Start index must be less than the end index.')
            self.ui.error_label.setVisible(True)
            return None, None

        if end_index > len(self.wavelengths):
            self.ui.error_label.setText('End index is out of range, setting to end point.')
            self.ui.error_label.setVisible(True)
            self._extra_message += ' End wavelength too high, using the last wavelength.'

            end_index = len(self.wavelengths)-1

        if end_index < 0:
            self.ui.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('End index is out of range.')
            self.ui.error_label.setVisible(True)

            end_index = None

        log.debug('  returning with start_index {} and end_index {}'.format(
            start_index, end_index))

        return start_index, end_index

    def _calculate_callback_simple_sigma_check(self):
        log.debug('_calculate_callback_simgple_sigma_check')

        simple_sigma = self.ui.simple_sigma_input.text().strip()
        log.debug('    simple_sigma {}'.format(simple_sigma))

        try:
            simple_sigma = float(simple_sigma)
        except:
            self.ui.simple_sigma_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Sigma must be a floating point number.')
            self.ui.error_label.setVisible(True)
            return None

        if simple_sigma <= 0.0:
            self.ui.simple_sigma_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Sigma must be a positive number.')
            self.ui.error_label.setVisible(True)
            return None

        return simple_sigma

    def _calculate_callback_advanced_sigma_check(self):
        sigma = self.ui.advanced_sigma_input.text().strip()
        sigma_lower = self.ui.advanced_sigma_lower_input.text().strip()
        sigma_upper = self.ui.advanced_sigma_upper_input.text().strip()
        sigma_iters = self.ui.advanced_sigma_iters_input.text().strip()

        if len(sigma) > 0:
            try:
                sigma = float(sigma)
            except:
                self.ui.advanced_sigma_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                self.ui.error_label.setText('Sigma must be a floating point number.')
                self.ui.error_label.setVisible(True)
                return None
        else:
            self.ui.advanced_sigma_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Sigma must be a floating point number and not empty.')
            self.ui.error_label.setVisible(True)
            return None, None, None, None

        if len(sigma_lower) > 0:
            try:
                sigma_lower = float(sigma_lower)
            except:
                self.ui.advanced_sigma_lower_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                self.ui.error_label.setText('Lower sigma must be a floating point number.')
                self.ui.error_label.setVisible(True)
                return [None]*4
        else:
            sigma_lower = None

        if len(sigma_upper) > 0:
            try:
                sigma_upper = float(sigma_upper)
            except:
                self.ui.advanced_sigma_upper_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                self.ui.error_label.setText('Upper sigma must be a floating point number.')
                self.ui.error_label.setVisible(True)
                return [None]*4
        else:
            sigma_upper = None

        if len(sigma_iters) > 0:
            try:
                sigma_iters = int(sigma_iters)
            except:
                self.ui.advanced_sigma_iters_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
                self.ui.error_label.setText('Iterations for sigma must be a floating point number.')
                self.ui.error_label.setVisible(True)
                return [None]*4
        else:
            sigma_iters = None

        if sigma_lower is not None and sigma_upper is not None and sigma_lower > sigma_upper:
            self.ui.advanced_sigma_lower_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.advanced_sigma_upper_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Lower sigma must be smaller than the upper sigma.')
            self.ui.error_label.setVisible(True)
            return [None]*4

        if sigma <= 0.0:
            self.ui.advanced_sigma_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Sigma must be a positive number.')
            self.ui.error_label.setVisible(True)
            return [None]*4

        return sigma, sigma_lower, sigma_upper, sigma_iters

    def _calculate_collapse(self, data_name, operation, spatial_region, sigma_selection, sigma_parameter, start_index, end_index):

        start_wavelength = self.wavelengths[start_index]
        end_wavelength = self.wavelengths[end_index]

        label = '{}-collapse-{} ({:.4e}, {:.4e})'.format(data_name, operation,
                                                         start_wavelength,
                                                         end_wavelength)

        # Setup the input_data (and apply the spatial mask based on
        # the selection in the spatial_region_combobox
        input_data = self.data[data_name]
        log.debug('    spatial region is {}'.format(spatial_region))
        if not spatial_region == 'Image':
            subset = [x.to_mask() for x in self.data.subsets if x.label == spatial_region][0]
            input_data = input_data * subset

        # Apply sigma clipping
        if 'Simple' in sigma_selection:
            sigma = sigma_parameter

            if sigma is None:
                return

            input_data = sigma_clip(input_data, sigma=sigma, axis=0)
            label += ' sigma={}'.format(sigma)

        elif 'Advanced' in sigma_selection:
            sigma, sigma_lower, sigma_upper, sigma_iters = sigma_parameter
            log.debug('    returned from calculate_callback_advanced_sigma_check with sigma {}  sigma_lower {}  sigma_upper {}  sigma_iters {}'.format(
                sigma, sigma_lower, sigma_upper, sigma_iters))

            if sigma is None:
                return

            input_data = sigma_clip(input_data, sigma=sigma, sigma_lower=sigma_lower,
                                       sigma_upper=sigma_upper, iters=sigma_iters, axis=0)

            # Add to label so it is clear which overlay/component is which
            if sigma:
                label += ' sigma={}'.format(sigma)

            if sigma_lower:
                label += ' sigma_lower={}'.format(sigma_lower)

            if sigma_upper:
                label += ' sigma_upper={}'.format(sigma_upper)

            if sigma_iters:
                label += ' sigma_iters={}'.format(sigma_iters)
        else:
            input_data = input_data # noop

        # Do calculation if we got this far
        new_wavelengths, new_component = collapse_cube(input_data, data_name, self.data.coords.wcs,
                                             operation, start_index, end_index)

        return new_wavelengths, new_component, label

    def clear_stylesheets(self):
        self.ui.start_label.setStyleSheet("color: rgba(0, 0, 0, 255)")
        self.ui.end_label.setStyleSheet("color: rgba(0, 0, 0, 255)")

        self.ui.simple_sigma_label.setStyleSheet("color: rgba(0, 0, 0, 255)")

        self.ui.advanced_sigma_label.setStyleSheet("color: rgba(0, 0, 0, 255)")
        self.ui.advanced_sigma_lower_label.setStyleSheet("color: rgba(0, 0, 0, 255)")
        self.ui.advanced_sigma_upper_label.setStyleSheet("color: rgba(0, 0, 0, 255)")
        self.ui.advanced_sigma_iters_label.setStyleSheet("color: rgba(0, 0, 0, 255)")

    def calculate_callback(self):
        """
        Callback for when they hit calculate
        :return:
        """

        log.debug('In calculate_callback()')

        self.clear_stylesheets()

        # Grab the values of interest
        data_name = self.data_combobox.currentText()
        using_wavelengths = not 'Indices' in self.region_combobox.currentText()
        start_value = self.ui.start_input.text().strip()
        end_value = self.ui.end_input.text().strip()
        log.debug('    data_name {}  using_wavelengths {}  start_value {}  end_value {}'.format(
            data_name, using_wavelengths, start_value, end_value))

        # Clear the style sheet errors
        self.ui.error_label.setText(' ')
        self.ui.error_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
        self.ui.error_label.setVisible(False)

        # Do check on wavelength/indices first.
        if using_wavelengths:
            start_index, end_index = self._calculate_callback_wavelength_checks(start_value, end_value)
        else:
            start_index, end_index = self._calculate_callback_index_checks(start_value, end_value)

        if start_index is None or end_index is None:
            return

        # Check to see if the wavelength (indices) are the same.
        if start_index == end_index:
            self.ui.start_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.end_label.setStyleSheet("color: rgba(255, 0, 0, 128)")
            self.ui.error_label.setText('Can not have both start and end wavelengths be the same.')
            self.ui.error_label.setVisible(True)
            return

        data_name = self.data_combobox.currentText()
        operation = self.operation_combobox.currentText()
        spatial_region = self.spatial_region_combobox.currentText()
        sigma_selection = self.sigma_combobox.currentText()

        # Get the start and end wavelengths from the newly created
        # spectral cube and use for labeling the cube.
        # Convert to the current units.
        start_wavelength = self.wavelengths[start_index]
        end_wavelength = self.wavelengths[end_index]

        if 'Simple' in sigma_selection:
            sigma_parameter = self._calculate_callback_simple_sigma_check()
            if sigma_parameter is None:
                return
        elif 'Advanced' in sigma_selection:
            sigma_parameter = self._calculate_callback_advanced_sigma_check()
            if sigma_parameter[0] is None:
                return
        else:
            sigma_parameter = None

        # Do the actual call.
        new_wavelengths, new_component, label = self._calculate_collapse(
                data_name, operation, spatial_region,
                sigma_selection, sigma_parameter,
                start_index, end_index)

        # Add new overlay/component to cubeviz. We add this both to the 2D
        # container Data object and also as an overlay. In future we might be
        # able to use the 2D container Data object for the overlays directly.

        try:
            add_to_2d_container(self.parent, self.data, new_component, label)
            self.parent.add_overlay(new_component, label, display_now=False)
        except Exception as e:
            show_error_message(str(e), 'Collapse Cube Error', parent=self)
            return
        finally:
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
        widget_desc = QLabel('The collapsed cube was added as an overlay with label "{}". {}'.format(
            label, self._extra_message))
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
