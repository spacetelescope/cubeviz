from __future__ import absolute_import, division, print_function

import numpy as np

from astropy import convolution

from glue.core import Data, Subset
from glue.core.coordinates import coordinates_from_header, WCSCoordinates
from glue.core.exceptions import IncompatibleAttribute

from spectral_cube import SpectralCube, BooleanArrayMask

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QMainWindow, QApplication, QPushButton,
    QLabel, QWidget, QHBoxLayout, QVBoxLayout,
    QComboBox, QMessageBox, QLineEdit, QRadioButton
)


class Smooth(object):

    def __init__(self, data=None, smoothing_axis=None, kernel_type=None, kernel_size=None,
                 component_id=None, output_label=None, output_as_component=False, parent=None):
        self.data = data  # Glue data to be smoothed
        self.smoothing_axis = smoothing_axis  # spectral vs spatial
        self.kernel_type = kernel_type  # Type of kernel, a key in kernel_registry
        self.kernel_size = kernel_size  # Size of kernel in pix
        self.component_id = component_id  # Glue data component to smooth over
        self.output_label = output_label  # Output label
        self.output_as_component = output_as_component  # Add output component to self.data
        self.kernel_registry = self.load_kernel_registry()  # A list of kernels and params
        self.parent = parent  # If gui is going to be used, parent of new gui

    @staticmethod
    def load_kernel_registry():
        """
        Nested dict to store available kernel options.

        kernel_registry: Main registry
            kernel_type: Type of kernel
                name: Display name
                unit_label: Display units of kernel size
                size_prompt: User prompt for size of kernel
                axis: Available axes. Each must have a kernel.
                spatial: 2D astropy.convolution.kernel else None.
                spectral: 1D astropy.convolution.kernel else None.

        :return: kernel_registry
        """
        kernel_registry = {
            "box": {"name": "Box",
                    "unit_label": "Pixels",
                    "size_prompt": "Width of Kernel:",
                    "axis": ["spatial", "spectral"],
                    "spatial": convolution.Box2DKernel,
                    "spectral": convolution.Box1DKernel},
            "gaussian": {"name": "Gaussian",
                         "unit_label": "Pixels",
                         "size_prompt": "Standard Deviation of Kernel:",
                         "axis": ["spatial", "spectral"],
                         "spatial": convolution.Gaussian2DKernel,
                         "spectral": convolution.Gaussian1DKernel},
            "mexicanhat": {"name": "Mexican Hat",
                           "unit_label": "Pixels",
                           "size_prompt": "Width of Kernel:",
                           "axis": ["spatial", "spectral"],
                           "spatial": convolution.MexicanHat2DKernel,
                           "spectral": convolution.MexicanHat1DKernel},
            "trapezoid": {"name": "Trapezoid",
                          "unit_label": "Pixels",
                          "size_prompt": "Width of Kernel:",
                          "axis": ["spatial"],
                          "spatial": convolution.Trapezoid1DKernel},
            "trapezoiddisk": {"name": "Trapezoid Disk",
                              "unit_label": "Pixels",
                              "size_prompt": "Radius of Kernel:",
                              "axis": ["spatial"],
                              "spatial": convolution.TrapezoidDisk2DKernel},
            "airydisk": {"name": "Airy Disk",
                         "unit_label": "Pixels",
                         "size_prompt": "Radius of Kernel:",
                         "axis": ["spatial"],
                         "spatial": convolution.AiryDisk2DKernel},
            "tophat": {"name": "Top Hat",
                       "unit_label": "Pixels",
                       "size_prompt": "Radius of Kernel:",
                       "axis": ["spatial"],
                       "spatial": convolution.Tophat2DKernel},
            "median": {"name": "Median",
                       "unit_label": "Pixels",
                       "size_prompt": "Width of Kernel:",
                       "axis": ["spatial", "spectral"],
                       "spatial": None,
                       "spectral": None}
        }
        return kernel_registry

    def get_kernel_registry(self):
        return self.kernel_registry
    
    def get_kernel(self):
        """
        Gets an kernel using the saved parameters
        :return: astropy.convolution.kernel
        """
        return self.kernel_registry[self.kernel_type][self.smoothing_axis](self.kernel_size)
    
    def get_kernel_size_prompt(self, kernel_type=None):
        """kernel_type -> size_prompt"""
        if kernel_type is None:
            if self.kernel_type is None:
                return None
            kernel_type = self.kernel_type
        if kernel_type not in self.kernel_registry:
            return None
        return self.kernel_registry[kernel_type]["size_prompt"]

    def get_kernel_unit(self, kernel_type=None):
        """kernel_type -> unit_label"""
        if kernel_type is None:
            if self.kernel_type is None:
                return None
            kernel_type = self.kernel_type
        if kernel_type not in self.kernel_registry:
            return None
        return self.kernel_registry[kernel_type]["unit_label"]

    def name_to_kernel_type(self, name):
        """kernel name -> kernel_type"""
        for k in self.kernel_registry:
            if name == self.kernel_registry[k]["name"]:
                return k
        return None
                
    def get_glue_wcs(self):
        """
        Get WCS of glue Data.
        :return: astropy.wcs.WCS
        :raises: Exception WCS not found
        """
        coords = self.data.coords
        if isinstance(coords, WCSCoordinates):
            return coords.wcs
        raise Exception("WCS information was not provided.")

    def get_glue_mask(self):
        """Function make/extract mask of glue Data"""
        if isinstance(self.data, Subset):
            try:
                mask = self.data.to_mask()
                return mask
            except IncompatibleAttribute:
                pass
        d = self.data[self.component_id]
        mask = np.empty_like(d)
        mask.fill(True)
        mask = mask.astype(bool)
        return mask

    def data_to_cube(self):
        """Glue Data -> SpectralCube"""
        if self.component_id is None:
            raise Exception("component_id was not provided.")
        wcs = self.get_glue_wcs()
        data_array = self.data[self.component_id]
        mask = BooleanArrayMask(
            mask=self.get_glue_mask(),
            wcs=wcs)
        cube = SpectralCube(data=data_array, wcs=wcs, mask=mask)
        return cube

    def cube_to_data(self, cube,
                     output_label=None,
                     output_component_id=None):
        """
        Convert SpectralCube to final output.
        self.output_as_component is checked here.
        if self.output_as_component:
            add new component to self.data
        else:
            create new data and return it.
        :param cube: SpectralCube
        :param output_label: Name of new Data.
        :param output_component_id: label of new component
        :return:
        """
        original_data = self.data
        if self.output_as_component:
            original_data.add_component(cube._data.copy(), output_component_id)
            return None
        else:
            new_data = Data(label=output_label)
            new_data.coords = coordinates_from_header(cube.header)
            new_data.add_component(cube._data.copy(), output_component_id)
            return new_data

    def smooth_cube(self):
        """
        Main smoothing function that follows the following steps:
        1) Convert data to SpectralCube
        2) Obtain Kernel using saved parameters (if applicable)
        3) Smooth cube
        4) Generate name based on saved parameters
        5) Output component or Data
        :return: glue.core.Data or None
        """
        cube = self.data_to_cube()

        if "median" == self.kernel_type:
            if self.smoothing_axis == "spatial":
                new_cube = cube.spatial_smooth_median(self.kernel_size)
            else:
                new_cube = cube.spectral_smooth_median(self.kernel_size)
        else:
            kernel = self.get_kernel()
            if self.smoothing_axis == "spatial":
                new_cube = cube.spatial_smooth(kernel)
            else:
                new_cube = cube.spectral_smooth(kernel)

        name_tail = "_" + "_".join(["smoothed",
                                    self.kernel_type,
                                    self.smoothing_axis,
                                    "%spixels" % self.kernel_size])

        if self.output_as_component:
            if self.output_label is None:
                output_component_id = self.component_id + name_tail
            else:
                output_component_id = self.output_label
            output = self.cube_to_data(new_cube, output_component_id=output_component_id)
        else:
            if self.output_label is None:
                output_label = self.data.label + name_tail
            else:
                output_label = self.output_label
            output = self.cube_to_data(new_cube,
                                       output_label=output_label,
                                       output_component_id=self.component_id)
        return output

    def gui(self):
        """Call smoothing gui and add output as component"""
        ex = SelectSmoothing(self.data, self.parent)


class SelectSmoothing(QMainWindow):
    """
    SelectSmoothing launches a GUI and executes smoothing.
    Any output is added to the input data as a new component.
    """

    def __init__(self, data, parent=None, smooth=None):
        super(SelectSmoothing, self).__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.parent = parent
        self.title = "Smoothing Selection"

        self.data = data  # Glue data to be smoothed

        # Check if smooth object is the caller
        if smooth is None:
            self.smooth = Smooth(data=self.data)
        else:
            self.smooth = smooth

        self.abort_window = None  # Small window pop up when smoothing.

        self.component_id = None  # Glue data component to smooth over
        self.current_axis = None  # Selected smoothing_axis
        self.current_kernel_type = None  # Selected kernel type, a key in Smooth.kernel_registry
        self.current_kernel_name = None  # Name of selected kernel

        self._init_selection_ui() # Format and show gui

    def _init_selection_ui(self):
        # LINE 1: Radio box spatial vs spectral axis
        self.axes_prompt = QLabel("Smoothing Axis:")
        self.axes_prompt.setMinimumWidth(150)

        self.spatial_radio = QRadioButton("Spatial")
        self.spatial_radio.setChecked(True)
        self.current_axis = "spatial"
        self.spatial_radio.toggled.connect(self.spatial_radio_checked)

        self.spectral_radio = QRadioButton("Spectral")
        self.spectral_radio.toggled.connect(self.spectral_radio_checked)

        # hbl is short for Horizontal Box Layout
        hbl1 = QHBoxLayout()
        hbl1.addWidget(self.axes_prompt)
        hbl1.addWidget(self.spatial_radio)
        hbl1.addWidget(self.spectral_radio)

        # LINE 2: Kernel Type prompt
        self.k_type_prompt = QLabel("Kernel Type:")
        self.k_type_prompt.setMinimumWidth(150)
        # Load kernel types + names and add to drop down
        self._load_options()
        self.combo = QComboBox()
        self.combo.setMinimumWidth(150)
        self.combo.addItems(self.options[self.current_axis])

        hbl2 = QHBoxLayout()
        hbl2.addWidget(self.k_type_prompt)
        hbl2.addWidget(self.combo)

        # LINE 3: Kernel size
        self.size_prompt = QLabel(self.smooth.get_kernel_size_prompt(self.current_kernel_type))
        self.size_prompt.setWordWrap(True)
        self.size_prompt.setMinimumWidth(150)
        self.unit_label = QLabel(self.smooth.get_kernel_unit(self.current_kernel_type))
        self.k_size = QLineEdit("1")  # Default Kernel size set here

        hbl3 = QHBoxLayout()
        hbl3.addWidget(self.size_prompt)
        hbl3.addWidget(self.k_size)
        hbl3.addWidget(self.unit_label)

        # LINE 4: Data component drop down
        self.component_prompt = QLabel("Data Component:")
        self.component_prompt.setWordWrap(True)
        self.component_prompt.setMinimumWidth(150)
        # Load component_ids and add to drop down
        component_ids = [str(i) for i in self.data.component_ids()]
        self.component_combo = QComboBox()
        self.component_combo.addItems(
            component_ids
        )

        self.component_combo.setMaximumWidth(150)
        if 'FLUX' in component_ids:
            self.component_combo.setCurrentIndex(component_ids.index('FLUX'))

        hbl4 = QHBoxLayout()
        hbl4.addWidget(self.component_prompt)
        hbl4.addWidget(self.component_combo)

        # LINE 5: ok cancel buttons
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.call_main)
        self.okButton.setDefault(True)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel)

        hbl5 = QHBoxLayout()
        hbl5.addStretch(1)
        hbl5.addWidget(self.cancelButton)
        hbl5.addWidget(self.okButton)

        # Add Lines to Vertical Layout
        # vbl is short for Vertical Box Layout
        vbl = QVBoxLayout()
        vbl.addLayout(hbl1)
        vbl.addLayout(hbl2)
        vbl.addLayout(hbl3)
        vbl.addLayout(hbl4)
        vbl.addLayout(hbl5)

        # Add Vertical Layout to Central Widget
        self.wid = QWidget(self)
        self.setCentralWidget(self.wid)
        self.wid.setLayout(vbl)

        self.setMaximumWidth(330)

        # Connect kernel combo box to event handler
        self.combo.currentIndexChanged.connect(self.selection_changed)
        self.selection_changed(0)

        self.show()

    def _load_options(self):
        """Extract names + types of kernels from Smooth.kernel_registry"""
        kernel_registry = self.smooth.get_kernel_registry()

        self.options = {"spatial": [], "spectral": []}
        for k in kernel_registry:
            axis = kernel_registry[k]["axis"]
            for a in axis:
                if "spatial" == a:
                    self.options["spatial"].append(kernel_registry[k]["name"])
                elif "spectral" == a:
                    self.options["spectral"].append(kernel_registry[k]["name"])
        self.options["spectral"].sort()
        self.options["spatial"].sort()
        self.current_kernel_name = self.options[self.current_axis][0]
        self.current_kernel_type = self.smooth.name_to_kernel_type(self.options[self.current_axis][0])

    def init_abort_ui(self):
        """
        init abort or notification ui.
        Displays while smoothing freezes the application.
        Allows abort button to be added if needed.
        """
        self.abort_window = QMainWindow(
            parent=self.parent,
            flags=Qt.WindowStaysOnTopHint)
        self.abort_window.setWindowFlags(
            self.abort_window.windowFlags() | Qt.Tool)

        label_a_1 = QLabel("Executing smoothing algorithm.")
        label_a_2 = QLabel("This may take several minutes.")

        # Add abort button here.

        # vbl is short for Vertical Box Layout
        vbl = QVBoxLayout()
        vbl.addWidget(label_a_1)
        vbl.addWidget(label_a_2)

        wid_abort = QWidget(self.abort_window)
        self.abort_window.setCentralWidget(wid_abort)
        wid_abort.setLayout(vbl)

        self.abort_window.show()

    def selection_changed(self, i):
        """
        Update kernel type, units, etc... when
        kernel name changes in combo box.
        """
        keys = self.options[self.current_axis]
        name = keys[i]
        self.current_kernel_name = name
        self.current_kernel_type = self.smooth.name_to_kernel_type(name)
        self.unit_label.setText(self.smooth.get_kernel_unit(self.current_kernel_type))
        self.size_prompt.setText(self.smooth.get_kernel_size_prompt(self.current_kernel_type))

    def spatial_radio_checked(self):
        self.current_axis = "spatial"
        self.combo.clear()
        self.combo.addItems(self.options[self.current_axis])

    def spectral_radio_checked(self):
        self.current_axis = "spectral"
        self.combo.clear()
        self.combo.addItems(self.options[self.current_axis])

    def input_validation(self):
        """
        Check if input will break Smoothing
        :return: bool: True if no errors
        """

        # Check 1: k_size
        if self.k_size == "":
            self.k_size.setStyleSheet("background-color: rgba(255, 0, 0, 128);")
            return False
        else:
            try:
                if self.current_kernel_type == "median":
                    k_size = int(self.k_size.text())
                else:
                    k_size = float(self.k_size.text())
            except ValueError:
                if self.current_kernel_type == "median":
                    info = QMessageBox.critical(self, "Error",
                                                "Kernel size must be integer for median")
                self.k_size.setStyleSheet("background-color: rgba(255, 0, 0, 128);")
                return False
            if k_size <= 0:
                return False
            self.k_size.setStyleSheet("")

        return True

    def call_main(self):
        try:
            self.main()
        except Exception as e:
            info = QMessageBox.critical(self, "Error", str(e))
            self.cancel()
            raise

    def main(self):
        """
        Main function to process input and call smoothing.smooth_cube
        """
        success = self.input_validation()

        if not success:
            return

        # Add smoothing parameters
        if self.smooth.data is None:
            self.smooth.data = self.data
        self.smooth.smoothing_axis = self.current_axis
        self.smooth.kernel_type = self.current_kernel_type
        self.smooth.kernel_size = int(self.k_size.text())
        self.smooth.component_id = str(self.component_combo.currentText())
        self.smooth.output_as_component = True

        self.hide()
        self.init_abort_ui()
        QApplication.processEvents()

        output = self.smooth.smooth_cube()

        info = QMessageBox.information(self, "Success",
                                       "Result added as a new component of the input Data")

        self.abort_window.close()
        self.close()
        return

    def cancel(self):
        self.close()
        if self.abort_window is not None:
            self.abort_window.close()
