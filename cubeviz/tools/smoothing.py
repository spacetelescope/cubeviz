from __future__ import absolute_import, division, print_function

import numpy as np
from scipy import ndimage

from astropy import convolution

from glue.core import Data, Subset, Component
from glue.core.coordinates import coordinates_from_header, WCSCoordinates
from glue.core.exceptions import IncompatibleAttribute
from glue.utils.qt import update_combobox

from spectral_cube import SpectralCube, BooleanArrayMask

from qtpy.QtCore import Qt, Signal, QThread
from qtpy.QtWidgets import (
    QDialog, QApplication, QPushButton, QProgressBar,
    QLabel, QWidget, QDockWidget, QHBoxLayout, QVBoxLayout,
    QComboBox, QMessageBox, QLineEdit, QRadioButton
)


class AbortException(Exception):
    """
    Custom exception to indicate a calculation abort.
    """
    pass


class WorkerThread(QThread):
    """
    Custom QThread for SmoothCube
    """

    success_signal = Signal()  # Smoothing is done
    error_signal = Signal(Exception)  # Smoothing failed

    def __init__(self, smooth_cube, parent=None):
        super(WorkerThread, self).__init__(parent)
        self.smooth_cube = smooth_cube

        self.success_signal.connect(self.smooth_cube.thread_callback)
        self.error_signal.connect(self.smooth_cube.thread_error_handler)

    def run(self):
        try:
            success_flag = self.smooth_cube.thread_function()
            if success_flag:
                self.success_signal.emit()
        except Exception as e:
            if not isinstance(e, AbortException):
                self.error_signal.emit(e)


class SmoothCube(object):
    """
    SmoothCube is a wrapper for SpectralCube. It is designed to
    operate in CubeViz and glue.
    It saves a registry of available kernels and executes
    smoothing operations. It has the ability to use QThreads
    when working in gui mode.
    """

    def __init__(self, data=None, smoothing_axis=None, kernel_type=None, kernel_size=None,
                 component_id=None, output_label=None, output_as_component=False, parent=None):
        self.data = data  # Glue data to be smoothed
        self.smoothing_axis = smoothing_axis  # spectral vs spatial
        self.kernel_type = kernel_type  # Type of kernel, a key in kernel_registry
        self.kernel_size = kernel_size  # Size of kernel in pix
        self.component_id = component_id  # Glue data component to smooth over
        self.component_unit = ''  # Units of component
        self.output_label = output_label  # Output label
        self.output_as_component = output_as_component  # Add output component to self.data
        self.kernel_registry = self.load_kernel_registry()  # A list of kernels and params

        self.parent = parent  # If gui is going to be used, parent of new gui

        # Vars for multi-threading smoothing
        self.is_multi_threading = False  # Using multi-threading?
        self.is_active = False  # Is thread active
        self.abort_window = None  # Abort window gui
        self.thread = None # QThread
        self.thread_cube = None  # Input SpectralCube
        self.thread_result = None  # Temporary storage for thread output

    @staticmethod
    def load_kernel_registry():
        """
        Nested dict to store available kernel options.

        kernel_registry: Main registry
            kernel_type: Type of kernel
                name: Display name
                unit_label: Display units of kernel size
                size_prompt: User prompt for size of kernel
                size_dimension: Dimension of kernel (width, radius, etc..)
                axis: Available axes. Each must have a kernel.
                spatial: 2D astropy.convolution.kernel else None.
                spectral: 1D astropy.convolution.kernel else None.

        :return: kernel_registry
        """
        kernel_registry = {
            "box": {"name": "Box",
                    "unit_label": "Spaxel",
                    "size_prompt": "Width of Kernel:",
                    "size_dimension": "Width",
                    "axis": ["spatial", "spectral"],
                    "spatial": convolution.Box2DKernel,
                    "spectral": convolution.Box1DKernel},
            "gaussian": {"name": "Gaussian",
                         "unit_label": "Spaxel",
                         "size_prompt": "Standard Deviation of Kernel:",
                         "size_dimension": "Sigma",
                         "axis": ["spatial", "spectral"],
                         "spatial": convolution.Gaussian2DKernel,
                         "spectral": convolution.Gaussian1DKernel},
            "trapezoid": {"name": "Trapezoid",
                          "unit_label": "Spaxel",
                          "size_prompt": "Width of Kernel:",
                          "size_dimension": "Width",
                          "axis": ["spectral"],
                          "spectral": convolution.Trapezoid1DKernel},
            "trapezoiddisk": {"name": "Trapezoid Disk",
                              "unit_label": "Spaxel",
                              "size_prompt": "Radius of Kernel:",
                              "size_dimension": "Radius",
                              "axis": ["spatial"],
                              "spatial": convolution.TrapezoidDisk2DKernel},
            "airydisk": {"name": "Airy Disk",
                         "unit_label": "Spaxel",
                         "size_prompt": "Radius of Kernel:",
                         "size_dimension": "Radius",
                         "axis": ["spatial"],
                         "spatial": convolution.AiryDisk2DKernel},
            "tophat": {"name": "Top Hat",
                       "unit_label": "Spaxel",
                       "size_prompt": "Radius of Kernel:",
                       "size_dimension": "Radius",
                       "axis": ["spatial"],
                       "spatial": convolution.Tophat2DKernel},
            "median": {"name": "Median",
                       "unit_label": "Spaxel",
                       "size_prompt": "Width of Kernel:",
                       "size_dimension": "Width",
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

    def get_kernel_size_dimension(self, kernel_type=None):
        """kernel_type -> size_dimension"""
        if kernel_type is None:
            if self.kernel_type is None:
                return None
            kernel_type = self.kernel_type
        if kernel_type not in self.kernel_registry:
            return None
        return self.kernel_registry[kernel_type]["size_dimension"]

    def name_to_kernel_type(self, name):
        """kernel name -> kernel_type"""
        for k in self.kernel_registry:
            if name == self.kernel_registry[k]["name"]:
                return k
        return None

    def kernel_type_to_name(self, kernel_type):
        """kernel_type -> kernel name"""
        for k in self.kernel_registry:
            if kernel_type == k:
                return self.kernel_registry[k]["name"]
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
        self.component_unit = self.data.get_component(self.component_id).units
        return SpectralCube(data=data_array, wcs=wcs, mask=mask)

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
        new_component = Component(cube._data.copy(), self.component_unit)
        if self.output_as_component:
            original_data.add_component(new_component, output_component_id)
            return None
        else:
            new_data = Data(label=output_label)
            new_data.coords = coordinates_from_header(cube.header)
            new_data.add_component(new_component, output_component_id)
            return new_data

    def unique_output_component_id(self):
        unit_label = self.kernel_registry[self.kernel_type]["unit_label"].lower()
        if self.kernel_size == 1:
            kernel_size_text = "{0}_{1}".format(self.kernel_size, unit_label)
        else:
            kernel_size_text = "{0}_{1}s".format(self.kernel_size, unit_label)

        name_tail = "_Smoothed(" + ", ".join([
                                            self.kernel_type_to_name(self.kernel_type),
                                            self.smoothing_axis.title(),
                                            kernel_size_text]) + ")"

        if self.output_label is None:
            output_component_id = self.component_id + name_tail
        else:
            output_component_id = self.output_label

        taken = [str(i) for i in self.data.component_ids()]
        index_list = []
        for name in taken:
            if output_component_id in name:
                if output_component_id == name:
                    index_list.append(0)
                else:
                    try:
                        idx = int(name.split("_")[-1])
                        index_list.append(idx)
                    except ValueError:
                        pass
        if len(index_list) > 0:
            idx = max(index_list) + 1
            return output_component_id + "_" + str(idx)
        return output_component_id

    def output_data_name(self):
        unit_label = self.kernel_registry[self.kernel_type]["unit_label"].lower()
        if self.kernel_size == 1:
            kernel_size_text = "{0}_{1}".format(self.kernel_size, unit_label)
        else:
            kernel_size_text = "{0}_{1}s".format(self.kernel_size, unit_label)

        name_tail = "_Smoothed(" + ", ".join([
                                            self.kernel_type_to_name(self.kernel_type),
                                            self.smoothing_axis.title(),
                                            kernel_size_text]) + ")"

        if self.output_label is None:
            return self.data.label + name_tail
        else:
            return self.output_label

    def smooth_cube(self, preview=False):
        """
        Main (serial) smoothing function that follows the following steps:
        1) Convert data to SpectralCube
        2) Obtain Kernel using saved parameters (if applicable)
        3) Smooth cube
        4) Generate name based on saved parameters
        5) Output component or Data
        :return: glue.core.Data or None
        """
        cube = self.data_to_cube()

        if "median" == self.kernel_type:
            if "spatial" == self.smoothing_axis:
                new_cube = cube.spatial_smooth_median(self.kernel_size)
            else:
                new_cube = cube.spectral_smooth_median(self.kernel_size)
        else:
            kernel = self.get_kernel()
            if "spatial" == self.smoothing_axis:
                new_cube = cube.spatial_smooth(kernel)
            else:
                new_cube = cube.spectral_smooth(kernel)

        if self.output_as_component:
            output_component_id = self.unique_output_component_id()
            output = self.cube_to_data(new_cube, output_component_id=output_component_id)
        elif preview:
            return cube._data.copy()
        else:
            output_label = self.output_data_name()
            output = self.cube_to_data(new_cube,
                                       output_label=output_label,
                                       output_component_id=self.component_id)

        return output

    def multi_threading_smooth(self):
        """
        Prepares data and starts worker thread.
        Overall steps accomplished:
            1) Convert data to SpectralCube and start thread
        """
        cube = self.data_to_cube()

        # Handshake b/w SpectralCube and AbortWindow
        if "spectral" == self.smoothing_axis:
            self.abort_window.init_pb(0, cube.shape[1]*cube.shape[2])
        else:
            self.abort_window.init_pb(0, cube.shape[0])

        self.thread_cube = cube
        self.thread = WorkerThread(self, self.parent)
        self.thread.start()

    def thread_function(self):
        """
        On-thread function that executes smoothing
        Overall steps accomplished:
            2) Obtain Kernel using saved parameters (if applicable)
            3) Smooth cube
        :return: bool: True if output is added to self.thread_result
        :raises: Exception: if output is not an instance of SpectralCube
        """
        success = True

        cube = self.thread_cube
        update_function = self.abort_window.update_pb
        if "median" == self.kernel_type:
            if "spatial" == self.smoothing_axis:
                new_cube = cube.spatial_smooth_median(self.kernel_size, update_function=update_function)
            else:
                new_cube = cube.spectral_smooth_median(self.kernel_size, update_function=update_function)
        else:
            kernel = self.get_kernel()
            if "spatial" == self.smoothing_axis:
                new_cube = cube.spatial_smooth(kernel, update_function=update_function)
            else:
                new_cube = cube.spectral_smooth(kernel, update_function=update_function)

        if isinstance(new_cube, SpectralCube):
            self.thread_result = new_cube
            return success
        else:
            raise Exception("Unexpected return type from SpectralCube.")

    def thread_callback(self):
        """
        Callback function for worker thread.
        Overall steps accomplished:
            4) Generate name based on saved parameters
            5) Output as component ONLY
        """
        output_component_id = self.unique_output_component_id()
        output = self.cube_to_data(self.thread_result, output_component_id=output_component_id)
        self.abort_window.smoothing_done(output_component_id)

    def thread_error_handler(self, exception):
        self.abort_window.print_error(exception)
        raise exception

    def gui(self):
        """Call smoothing gui and add output as component"""
        ex = SelectSmoothing(self.data, self.parent)

    def preview_smoothing(self, data):
        if "median" == self.kernel_type:
            return ndimage.filters.median_filter(data, self.kernel_size)
        else:
            kernel = self.get_kernel()
            return convolution.convolve(data, kernel, normalize_kernel=True)

    def get_preview_title(self):
        title = "Smoothing Preview: "
        title += self.kernel_type_to_name(self.kernel_type)
        size_dimension = self.get_kernel_size_dimension(self.kernel_type)
        unit_label = self.kernel_registry[self.kernel_type]["unit_label"].lower()
        if self.kernel_size == 1:
            title += "({0} = {1} {2})".format(size_dimension, self.kernel_size, unit_label)
        else:
            title += "({0} = {1} {2}s)".format(size_dimension, self.kernel_size, unit_label)
        return title


class AbortWindow(QDialog):
    """
    Displays busy message and provides abort button.
    The class serves SmoothCube, WorkerThread and SelectSmoothing.
    """

    def __init__(self, parent=None):
        """
        init abort or notification ui.
        Displays while smoothing freezes the application.
        Allows abort button to be added if needed.
        """
        super(AbortWindow, self).__init__(parent)
        self.setModal(False)
        self.setWindowFlags(self.windowFlags() | Qt.Tool | Qt.WindowStaysOnTopHint)

        self.parent = parent

        self.label_a_1 = QLabel("Executing smoothing algorithm.")
        self.label_a_2 = QLabel("This may take several minutes.")

        self.abort_button = QPushButton("Abort")
        self.abort_button.clicked.connect(self.abort)

        self.pb = QProgressBar(self)
        self.pb_counter = 0

        self.abort_flag = False

        # vbl is short for Vertical Box Layout
        vbl = QVBoxLayout()
        vbl.addWidget(self.label_a_1)
        vbl.addWidget(self.label_a_2)
        vbl.addWidget(self.pb)
        vbl.addWidget(self.abort_button)

        self.setLayout(vbl)

        self.show()

    def init_pb(self, start, end):
        """
        Init the progress bar
        :param start: Start Value
        :param end: End Value
        """
        self.pb.setRange(start, end)
        self.pb_counter = start

    def update_pb(self):
        """
        This function is called in the worker thread to
        update the progress bar and checks if the
        local class variable abort_flag is active.

        If the abort button is clicked, the main thread
        will set abort_flag to True. The next time the
        worker thread calls this function, a custom
        exception is raised terminating the calculation.
        The exception is handled by the WorkerThread class.
        :raises: AbortException: terminating smoothing calculation
        """
        if self.abort_flag:
            raise AbortException("Abort Calculation")
        self.pb_counter += 1
        self.pb.setValue(self.pb_counter)
        QApplication.processEvents()

    def abort(self):
        """Abort calculation"""
        self.abort_flag = True
        self.parent.clean_up()

    def smoothing_done(self, component_id=None):
        """Notify user success"""
        self.hide()
        if component_id is None:
            message = "The result has been added as a" \
                      " new component of the input Data." \
                      " The new component can be accessed" \
                      " in the viewer drop-downs."
        else:
            message = "The result has been added as" \
                      " \"{0}\" and can be selected" \
                      " in the viewer drop-down menu.".format(component_id)

        info = QMessageBox.information(self, "Success", message)
        self.clean_up()

    def print_error(self, exception):
        """Print error message"""

        if "signal only works in main thread" in str(exception):
            message = "Smoothing Failed!\n\n" + "Please update your SpectralCube package"
        else:
            message = "Smoothing Failed!\n\n" + str(exception)

        info = QMessageBox.critical(self, "Error", message)
        self.clean_up()

    def clean_up(self):
        self.parent.clean_up()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.abort()


class SelectSmoothing(QDialog):
    """
    SelectSmoothing launches a GUI and executes smoothing.
    Any output is added to the input data as a new component.
    """

    def __init__(self, data, parent=None, smooth_cube=None,
                 allow_preview=False, allow_spectral_axes=False):
        super(SelectSmoothing, self).__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.parent = parent
        self.title = "Smoothing Selection"

        self.data = data  # Glue data to be smoothed

        # Check if smooth object is the caller
        if smooth_cube is None:
            self.smooth_cube = SmoothCube(data=self.data)
        else:
            self.smooth_cube = smooth_cube

        self.allow_spectral_axes = allow_spectral_axes

        self.allow_preview = allow_preview
        self.is_preview_active = False  # Flag to show if smoothing preview is active

        self.abort_window = None  # Small window pop up when smoothing.

        self.component_id = None  # Glue data component to smooth over
        self.current_axis = None  # Selected smoothing_axis
        self.current_kernel_type = None  # Selected kernel type, a key in SmoothCube.kernel_registry
        self.current_kernel_name = None  # Name of selected kernel

        self._init_selection_ui()  # Format and show gui

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
        self.size_prompt = QLabel(self.smooth_cube.get_kernel_size_prompt(self.current_kernel_type))
        self.size_prompt.setWordWrap(True)
        self.size_prompt.setMinimumWidth(150)
        self.unit_label = QLabel(self.smooth_cube.get_kernel_unit(self.current_kernel_type))
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

        # Add the data component labels to the drop down, with the ComponentID
        # set as the userData:

        if self.parent is not None and hasattr(self.parent, 'data_components'):
            labeldata = [(str(cid), cid) for cid in self.parent.data_components]
        else:
            labeldata = [(str(cid), cid) for cid in self.data.main_components()]

        self.component_combo = QComboBox()
        update_combobox(self.component_combo, labeldata)

        self.component_combo.setMaximumWidth(150)
        self.component_combo.setCurrentIndex(0)
        if self.allow_preview:
            self.component_combo.currentIndexChanged.connect(self.update_preview_button)

        hbl4 = QHBoxLayout()
        hbl4.addWidget(self.component_prompt)
        hbl4.addWidget(self.component_combo)

        # Line 5: Preview Message
        message = "Info: Smoothing previews are displayed on " \
                  "CubeViz's left and single image viewers."
        self.preview_message = QLabel(message)
        self.preview_message.setWordWrap(True)
        self.preview_message.hide()
        hbl5 = QHBoxLayout()
        hbl5.addWidget(self.preview_message)

        # LINE 6: preview ok cancel buttons
        self.previewButton = QPushButton("Preview Slice")
        self.previewButton.clicked.connect(self.call_preview)

        self.okButton = QPushButton("Smooth Cube")
        self.okButton.clicked.connect(self.call_main)
        self.okButton.setDefault(True)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel)

        hbl6 = QHBoxLayout()
        hbl6.addStretch(1)
        if self.allow_preview:
            hbl6.addWidget(self.previewButton)
        hbl6.addWidget(self.cancelButton)
        hbl6.addWidget(self.okButton)

        # Add Lines to Vertical Layout
        # vbl is short for Vertical Box Layout
        vbl = QVBoxLayout()
        if self.allow_spectral_axes:
            vbl.addLayout(hbl1)
        vbl.addLayout(hbl2)
        vbl.addLayout(hbl3)
        vbl.addLayout(hbl4)
        vbl.addLayout(hbl5)
        vbl.addLayout(hbl6)

        self.setLayout(vbl)
        self.setMaximumWidth(330)

        # Connect kernel combo box to event handler
        self.combo.currentIndexChanged.connect(self.selection_changed)
        self.selection_changed(0)

        self.show()

    def _load_options(self):
        """Extract names + types of kernels from SmoothCube.kernel_registry"""
        kernel_registry = self.smooth_cube.get_kernel_registry()

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
        self.current_kernel_type = self.smooth_cube.name_to_kernel_type(self.options[self.current_axis][0])

    def selection_changed(self, i):
        """
        Update kernel type, units, etc... when
        kernel name changes in combo box.
        """
        keys = self.options[self.current_axis]
        name = keys[i]
        self.current_kernel_name = name
        self.current_kernel_type = self.smooth_cube.name_to_kernel_type(name)
        self.unit_label.setText(self.smooth_cube.get_kernel_unit(self.current_kernel_type))
        self.size_prompt.setText(self.smooth_cube.get_kernel_size_prompt(self.current_kernel_type))

    def spatial_radio_checked(self):
        self.current_axis = "spatial"
        self.update_preview_button()
        self.combo.clear()
        self.combo.addItems(self.options[self.current_axis])

    def spectral_radio_checked(self):
        self.current_axis = "spectral"
        self.update_preview_button()
        self.combo.clear()
        self.combo.addItems(self.options[self.current_axis])

    def input_validation(self):
        """
        Check if input will break Smoothing
        :return: bool: True if no errors
        """
        red = "background-color: rgba(255, 0, 0, 128);"
        success = True

        # Check 1: k_size
        if self.k_size == "":
            self.k_size.setStyleSheet(red)
            success = False
        else:
            try:
                if self.current_kernel_type == "median":
                    k_size = int(self.k_size.text())
                else:
                    k_size = float(self.k_size.text())
                if k_size <= 0:
                    self.k_size.setStyleSheet(red)
                    success = False
                else:
                    self.k_size.setStyleSheet("")
            except ValueError:
                if self.current_kernel_type == "median":
                    info = QMessageBox.critical(self, "Error",
                                                "Kernel size must be integer for median")
                self.k_size.setStyleSheet(red)
                success = False

        return success

    def call_main(self):
        try:
            self.main()
        except Exception as e:
            info = QMessageBox.critical(self, "Error", str(e))
            self.cancel()
            raise

    def main(self):
        """
        Main function to process input and call smoothing function
        """
        success = self.input_validation()

        if not success:
            return

        self.hide()
        self.abort_window = AbortWindow(self)
        QApplication.processEvents()

        # Add smoothing parameters

        self.smooth_cube.abort_window = self.abort_window
        if self.smooth_cube.parent is None and self.parent is not self.smooth_cube:
            self.smooth_cube.parent = self.parent
        if self.parent is not self.smooth_cube:
            self.smooth_cube.data = self.data
        self.smooth_cube.smoothing_axis = self.current_axis
        self.smooth_cube.kernel_type = self.current_kernel_type
        if self.current_kernel_type == "median":
            self.smooth_cube.kernel_size = int(self.k_size.text())
        else:
            self.smooth_cube.kernel_size = float(self.k_size.text())
        self.smooth_cube.component_id = str(self.component_combo.currentText())
        self.smooth_cube.output_as_component = True

        if self.is_preview_active:
            self.parent.end_smoothing_preview()
            self.is_preview_active = False
        self.smooth_cube.multi_threading_smooth()
        return

    def update_preview_button(self):
        if self.parent is None or "spatial" != self.current_axis:
            self.previewButton.setDisabled(True)
            return
        self.previewButton.setDisabled(False)
        return

    def call_preview(self):
        try:
            self.preview()
        except Exception as e:
            info = QMessageBox.critical(self, "Error", str(e))
            self.cancel()
            raise

    def preview(self):
        """Preview current options"""
        success = self.input_validation()

        if not success:
            return

        if self.smooth_cube.parent is None and self.parent is not self.smooth_cube:
            self.smooth_cube.parent = self.parent
        self.smooth_cube.smoothing_axis = self.current_axis
        self.smooth_cube.kernel_type = self.current_kernel_type
        if self.current_kernel_type == "median":
            self.smooth_cube.kernel_size = int(self.k_size.text())
        else:
            self.smooth_cube.kernel_size = float(self.k_size.text())

        preview_function = self.smooth_cube.preview_smoothing
        preview_title = self.smooth_cube.get_preview_title()
        component_id = self.component_combo.currentData()
        self.parent.start_smoothing_preview(preview_function, component_id, preview_title)

        self.is_preview_active = True
        self.preview_message.show()

    def cancel(self):
        self.clean_up()

    def clean_up(self):
        self.close()
        if self.abort_window is not None:
            self.abort_window.close()
        if self.is_preview_active:
            self.parent.end_smoothing_preview()
            self.is_preview_active = False

    def closeEvent(self, event):
        if self.is_preview_active:
            self.parent.end_smoothing_preview()
            self.is_preview_active = False

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.clean_up()
