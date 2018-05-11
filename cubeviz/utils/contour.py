import os
import matplotlib.cm as cm

from qtpy.QtWidgets import (QLabel, QAction, QActionGroup,
                            QDialog, QHBoxLayout, QVBoxLayout,
                            QPushButton, QCheckBox, QLineEdit,
                            QGroupBox, QGridLayout, QMessageBox)
from qtpy.QtCore import Qt

from glue.config import viewer_tool
from glue.config import colormaps as glue_colormaps
from glue.utils.qt import QColormapCombo

from glue.viewers.common.qt.tool import Tool

DEFAULT_GLUE_COLORMAP_INDEX = 3
DEFAULT_CONTOUR_FONT_SIZE = 10
ICON_PATH = os.path.abspath(
    os.path.join(
        os.path.abspath(__file__),
        "..",
        "..",
        "data",
        "resources",
        "contour_icon.png"
    )
)

@viewer_tool
class ContourButton(Tool):
    """
    Contour map tool bar menu and button
    """
    icon = ICON_PATH
    tool_id = 'cubeviz:contour'
    action_text = 'Toggles contour map'
    tool_tip = 'Toggles contour map'
    status_tip = ''
    shortcut = None

    def __init__(self, viewer):
        super(ContourButton, self).__init__(viewer)
        self.tool_bar = self.viewer.toolbar
        if self.viewer.cubeviz_layout is not None:
            self.cubeviz_layout = self.viewer.cubeviz_layout
        else:
            self.cubeviz_layout = None

        self.options = None

    def activate(self):
        pass

    def menu_actions(self):
        """
        List of QtWidgets.QActions to be attached to this tool
        as a context menu.
        """
        self.options = []

        # WARNING: QAction labels are used to identify them.
        #          Changing them can cause problems unless
        #          all references are updated in this package.
        component_action_group = QActionGroup(self.tool_bar)

        action = QAction("Off", self.tool_bar, checkable=True)
        action.setChecked(True)
        action.setActionGroup(component_action_group)
        action.triggered.connect(self.viewer.remove_contour)
        self.options.append(action)

        action = QAction("Current Component", self.tool_bar, checkable=True)
        action.setActionGroup(component_action_group)
        action.triggered.connect(self.viewer.default_contour)
        self.options.append(action)

        action = QAction("Other Component", self.tool_bar, checkable=True)
        action.setActionGroup(component_action_group)
        action.triggered.connect(self.viewer.custom_contour)
        self.options.append(action)

        action = QAction(" ", self.tool_bar)
        action.setSeparator(True)
        self.options.append(action)

        action = QAction("Contour Settings", self.tool_bar)
        action.triggered.connect(self.viewer.edit_contour_settings)
        self.options.append(action)

        return self.options


class ContourOptionsDialog(QDialog):
    """
    Dialog box for selecting contour options
    """
    def __init__(self, contour_settings):
        super(ContourOptionsDialog, self).__init__(contour_settings.cubeviz_layout)
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.setWindowTitle("Contour Options")

        self.is_preview_active = False  # preview mode?

        self.contour_settings = contour_settings  # ref to caller ContourSettings
        self.image_viewer = self.contour_settings.image_viewer  # ref to image viewer
        self.options = self.contour_settings.options  # ref to ContourSettings options

        self._colormap_members = self.contour_settings.colormap_members  # Colormap options
        self._colormap_index = DEFAULT_GLUE_COLORMAP_INDEX  # Currently selected colormap
        if "cmap" in self.options:
            if self.options["cmap"] in self._colormap_members:
                self._colormap_index = self._colormap_members.index(self.options["cmap"])

        # Is there a user spacing?
        if self.contour_settings.spacing is None:
            self.is_custom_spacing = False
        else:
            self.is_custom_spacing = True
        # Is there a user min?
        if self.contour_settings.vmin is None:
            self.is_vmin = False
        else:
            self.is_vmin = True
        # Is there a user max?
        if self.contour_settings.vmax is None:
            self.is_vmax = False
        else:
            self.is_vmax = True

        self.add_contour_label = self.contour_settings.add_contour_label  # bool

        self._init_ui()

    def _init_ui(self):

        # Line 1: Color map
        self.colormap_label = QLabel("Color Scheme: ")

        self.colormap_combo = QColormapCombo()
        self.colormap_combo.addItem("", userData=cm.viridis)
        self.colormap_combo._update_icons()
        self.colormap_combo.setCurrentIndex(self._colormap_index)
        self.colormap_combo.setMaximumWidth(150)
        self.colormap_combo.currentIndexChanged.connect(
            self._on_colormap_change)

        #   hbl is short for Horizontal Box Layout
        hbl1 = QHBoxLayout()
        hbl1.addWidget(self.colormap_label)
        hbl1.addWidget(self.colormap_combo)

        # Line 2: Display contour labels
        self.contour_label_checkBox = QCheckBox("Contour labels (font size):")
        if self.contour_settings.add_contour_label:
            self.contour_label_checkBox.setChecked(True)
        self.contour_label_checkBox.toggled.connect(self.toggle_labels)

        font_string = str(self.contour_settings.font_size)
        self.font_size_input = QLineEdit(font_string)
        self.font_size_input.setFixedWidth(150)
        self.font_size_input.setDisabled(
            not self.contour_settings.add_contour_label)

        hbl2 = QHBoxLayout()
        hbl2.addWidget(self.contour_label_checkBox)
        hbl2.addWidget(self.font_size_input)

        # Line 3: Contour Spacing
        self.custom_spacing_checkBox = QCheckBox("Contour spacing (interval):")
        if self.is_custom_spacing:
            self.custom_spacing_checkBox.setChecked(True)
        self.custom_spacing_checkBox.toggled.connect(self.custom_spacing)

        self.spacing_input = QLineEdit()
        self.spacing_input.setFixedWidth(150)
        self.spacing_input.setDisabled(not self.is_custom_spacing)
        spacing = ""
        if self.is_custom_spacing:
            spacing = str(self.contour_settings.spacing)
        elif self.contour_settings.data_spacing is not None:
            spacing = self.contour_settings.data_spacing
            spacing = "{0:1.4f}".format(spacing)
        self.spacing_default_text = spacing
        self.spacing_input.setText(spacing)

        hbl3 = QHBoxLayout()
        hbl3.addWidget(self.custom_spacing_checkBox)
        hbl3.addWidget(self.spacing_input)

        # Line 4: Vmax
        self.vmax_checkBox = QCheckBox("Set max:")

        self.vmax_input = QLineEdit()
        self.vmax_input.setFixedWidth(150)
        self.vmax_input.setDisabled(not self.is_vmax)

        vmax = ""
        if self.is_vmax:
            self.vmax_checkBox.setChecked(True)
            vmax = str(self.contour_settings.vmax)
        elif self.contour_settings.data_max is not None:
            vmax = self.contour_settings.data_max
            vmax = "{0:1.4f}".format(vmax)
        self.vmax_input.setText(vmax)
        self.vmax_default_text = vmax

        self.vmax_checkBox.toggled.connect(self.toggle_vmax)

        hbl4 = QHBoxLayout()
        hbl4.addWidget(self.vmax_checkBox)
        hbl4.addWidget(self.vmax_input)

        # Line 5: Vmin
        self.vmin_checkBox = QCheckBox("Set min:")

        self.vmin_input = QLineEdit()
        self.vmin_input.setFixedWidth(150)
        self.vmin_input.setDisabled(not self.is_vmin)

        vmin = ""
        if self.is_vmin:
            self.vmin_checkBox.setChecked(True)
            vmin = str(self.contour_settings.vmin)
        elif self.contour_settings.data_min is not None:
            vmin = self.contour_settings.data_min
            vmin = "{0:1.4f}".format(vmin)
        self.vmin_input.setText(vmin)
        self.vmin_default_text = vmin

        self.vmin_checkBox.toggled.connect(self.toggle_vmin)

        hbl5 = QHBoxLayout()
        hbl5.addWidget(self.vmin_checkBox)
        hbl5.addWidget(self.vmin_input)

        # Line f:
        self.previewButton = QPushButton("Preview")
        self.previewButton.clicked.connect(self.preview)

        self.defaultButton = QPushButton("Reset")
        self.defaultButton.clicked.connect(self.default)

        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.finish)
        self.okButton.setDefault(True)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel)

        hblf = QHBoxLayout()
        hblf.addStretch(1)
        hblf.addWidget(self.previewButton)
        hblf.addWidget(self.defaultButton)
        hblf.addWidget(self.cancelButton)
        hblf.addWidget(self.okButton)

        vbl = QVBoxLayout()
        vbl.addLayout(hbl1)
        vbl.addLayout(hbl2)
        vbl.addLayout(hbl3)
        vbl.addLayout(hbl4)
        vbl.addLayout(hbl5)
        vbl.addLayout(hblf)

        self.setLayout(vbl)

        self.show()

    def update_data_vals(self, vmin="", vmax="", spacing="1"):

        self.vmin_default_text = vmin

        if not self.is_vmin:
            self.vmin_input.setText(vmin)

        self.vmax_default_text = vmax
        if not self.is_vmax:
            self.vmax_input.setText(vmax)

        self.spacing_default_text = spacing
        if not self.is_custom_spacing:
            self.spacing_input.setText(spacing)

    def _on_colormap_change(self, index):
        """Combo index changed handler"""
        self._colormap_index = index

    def custom_spacing(self):
        """Checkbox toggled handler"""
        if self.is_custom_spacing:
            self.is_custom_spacing = False
            self.spacing_input.setDisabled(True)
            spacing = ""
            if self.contour_settings.data_spacing:
                spacing = self.contour_settings.data_spacing
                spacing = "{0:1.4f}".format(spacing)
            self.spacing_input.setText(spacing)
            self.spacing_input.setStyleSheet("")
        else:
            self.is_custom_spacing = True
            self.spacing_input.setDisabled(False)

    def toggle_labels(self):
        """Checkbox toggled handler"""
        if self.add_contour_label:
            self.add_contour_label = False
            self.font_size_input.setDisabled(True)
            font_string = str(self.contour_settings.font_size)
            self.font_size_input.setText(font_string)
            self.font_size_input.setStyleSheet("")
        else:
            self.add_contour_label = True
            self.font_size_input.setDisabled(False)

    def toggle_vmax(self):
        """Checkbox toggled handler"""
        if self.is_vmax:
            self.is_vmax = False
            self.vmax_input.setDisabled(True)
            vmax = ""
            if self.contour_settings.data_max:
                vmax = self.contour_settings.data_max
                vmax = "{0:1.4f}".format(vmax)
            self.vmax_input.setText(vmax)
            self.vmax_input.setStyleSheet("")
        else:
            self.is_vmax = True
            self.vmax_input.setDisabled(False)

    def toggle_vmin(self):
        """Checkbox toggled handler"""
        if self.is_vmin:
            self.is_vmin = False
            self.vmin_input.setDisabled(True)
            vmin = ""
            if self.contour_settings.data_min:
                vmin = self.contour_settings.data_min
                vmin = "{0:1.4f}".format(vmin)
            self.vmin_input.setText(vmin)
            self.vmin_input.setStyleSheet("")
        else:
            self.is_vmin = True
            self.vmin_input.setDisabled(False)

    def input_validation(self):
        red = "background-color: rgba(255, 0, 0, 128);"

        def float_check(min_val=None):
            if user_input.text() == "":
                user_input.setStyleSheet(red)
                return False
            else:
                try:
                    value = float(user_input.text())
                    if min_val is not None:
                        if value <= min_val:
                            user_input.setStyleSheet(red)
                            return False
                    else:
                        user_input.setStyleSheet("")
                except ValueError:
                    user_input.setStyleSheet(red)
                    return False
            return True

        def int_check(min_val=None):
            if user_input.text() == "":
                user_input.setStyleSheet(red)
                return False
            else:
                try:
                    value = int(user_input.text())
                    if min_val is not None:
                        if value <= min_val:
                            user_input.setStyleSheet(red)
                            return False
                    else:
                        user_input.setStyleSheet("")
                except ValueError:
                    user_input.setStyleSheet(red)
                    return False
            return True

        success = True

        # Check 1: spacing_input
        if self.is_custom_spacing:
            user_input = self.spacing_input
            float_check(0)
            success = success and float_check()

        # Check 2: font_size_input
        if self.add_contour_label:
            user_input = self.font_size_input
            int_check(0)
            success = success and int_check()

        # Check 3: vmax
        if self.is_vmax:
            user_input = self.vmax_input
            float_check()
            success = success and float_check()

        # Check 4: vmax
        if self.is_vmin:
            user_input = self.vmin_input
            float_check()
            success = success and float_check()

        # Check 5: vmax and vmin
        if self.is_vmax and self.is_vmin and success:
            vmax = float(self.vmax_input.text())
            vmin = float(self.vmin_input.text())
            if vmax <= vmin:
                self.vmax_input.setStyleSheet(red)
                self.vmin_input.setStyleSheet(red)
                success = False

        return success

    def finish(self):
        """
        Ok button pressed. Finalize
        options and send to image viewer
         """
        success = self.input_validation()

        if not success:
            return

        # Change Color Map
        self._colormap_index = self.colormap_combo.currentIndex()
        colormap = self._colormap_members[self._colormap_index]
        self.contour_settings.options["cmap"] = colormap

        # labels
        self.contour_settings.add_contour_label = self.add_contour_label

        # font size
        if self.add_contour_label:
            font_size = int(self.font_size_input.text())
            self.contour_settings.font_size = font_size
        else:
            self.contour_settings.font_size = DEFAULT_CONTOUR_FONT_SIZE

        # Spacing
        if self.is_custom_spacing:
            self.contour_settings.spacing = float(self.spacing_input.text())
        else:
            self.contour_settings.spacing = None

        # vmax
        if self.is_vmax:
            vmax = float(self.vmax_input.text())
            self.contour_settings.vmax = vmax
            self.contour_settings.options["vmax"] = vmax
        else:
            self.contour_settings.vmax = None
            self.contour_settings.options["vmax"] = None

        # vmin
        if self.is_vmin:
            vmin = float(self.vmin_input.text())
            self.contour_settings.vmin = vmin
            self.contour_settings.options["vmin"] = vmin
        else:
            self.contour_settings.vmin = None
            self.contour_settings.options["vmin"] = None

        # Redraw contour
        if self.contour_settings.image_viewer.is_contour_active:
            self.contour_settings.draw_function()

        self.close()

    def preview(self):
        """
        Prepare preview contour settings
        and send to image viewer
        """
        success = self.input_validation()

        if not success:
            return

        image_viewer = self.contour_settings.image_viewer
        preview_settings = ContourSettings(image_viewer)
        preview_settings.dialog = self
        preview_settings.options = self.contour_settings.options.copy()
        preview_settings.spacing = self.contour_settings.spacing

        # Change Color Map
        self._colormap_index = self.colormap_combo.currentIndex()
        colormap = self._colormap_members[self._colormap_index]
        preview_settings.options["cmap"] = colormap

        # labels
        add_contour_label = self.contour_label_checkBox.isChecked()
        preview_settings.add_contour_label = add_contour_label

        # font size
        if add_contour_label:
            font_size = int(self.font_size_input.text())
            preview_settings.font_size = font_size

        # Spacing
        if self.is_custom_spacing:
            preview_settings.spacing = float(self.spacing_input.text())
        else:
            preview_settings.spacing = None

        # vmax
        if self.is_vmax:
            vmax = float(self.vmax_input.text())
            preview_settings.vmax = vmax
            preview_settings.options["vmax"] = vmax
        else:
            preview_settings.vmax = None
            preview_settings.options["vmax"] = None

        # vmin
        if self.is_vmin:
            vmin = float(self.vmin_input.text())
            preview_settings.vmin = vmin
            preview_settings.options["vmin"] = vmin
        else:
            preview_settings.vmin = None
            preview_settings.options["vmin"] = None

        # Redraw contour
        if image_viewer.is_contour_active:
            self.is_preview_active = True
            image_viewer.set_contour_preview(preview_settings)
        else:
            message = "Contour map is currently switched off. " \
                      "Please turn on the contour map by selecting " \
                      "a component from the contour map drop-down menu."
            info = QMessageBox.critical(self, "Error", message)

    def default(self):
        """
        Set options back to default
        and send to image viewer
        """
        self.contour_settings.options = self.contour_settings.default_options()
        self.contour_settings.spacing = None
        self.contour_settings.font_size = DEFAULT_CONTOUR_FONT_SIZE
        self.contour_settings.vmax = None
        self.contour_settings.vmin = None
        self.contour_settings.add_contour_label = False
        if self.contour_settings.image_viewer.is_contour_active:
            self.contour_settings.draw_function()
        self.contour_settings.options_dialog()

    def cancel(self):
        if self.contour_settings.image_viewer.is_contour_active:
            self.contour_settings.draw_function()
        self.close()

    def closeEvent(self, event):
        """closeEvent handler"""
        if self.is_preview_active:
            self.contour_settings.image_viewer.end_contour_preview()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.cancel()


class ContourSettings(object):
    """
    A class that contains contour settings.
    Settings
    ---------
    options : dict
        Holds kwargs to matplotlib.axes.Axes.contour
    spacing : int
        Spacing between contours
    vmax and vmin: float and float
        max and min values of the contour
    """
    def __init__(self, image_viewer, data_max=None,
                 data_min=None, data_spacing=None):
        self.image_viewer = image_viewer
        self.cubeviz_layout = self.image_viewer.cubeviz_layout
        self.draw_function = self.image_viewer.draw_contour

        self.options = self.default_options()

        self.spacing = None  # contour spacing

        self.add_contour_label = False  # add valye labels?
        self.font_size = DEFAULT_CONTOUR_FONT_SIZE

        self.vmax = None # Max value of contour
        self.vmin = None # Min value of contour

        # Load colormap options
        #   Add viridis to drop down
        self.colormap_members = [m[1] for m in glue_colormaps.members]
        self.colormap_members.append(cm.viridis)

        # Default data values
        self.data_max = data_max
        self.data_min = data_min
        self.data_spacing = data_spacing

        # Dialog
        self.dialog = None

    @staticmethod
    def default_options():
        options = {"cmap": cm.viridis}

        return options

    def options_dialog(self):
        """
        Open UI to change settings
        :return: qtpy.QtWidgets.QDialog
        """
        if self.dialog is not None:
            self.dialog.close()
        self.dialog = ContourOptionsDialog(self)
        return self.dialog

    def update_dialog(self):
        vmin = ""
        if self.data_min is not None:
            vmin = "{0:1.4f}".format(self.data_min)
        vmax = ""
        if self.data_max is not None:
            vmax = "{0:1.4f}".format(self.data_max)

        spacing = ""
        if self.data_spacing is not None:
            spacing = "{0:1.4f}".format(self.data_spacing)

        self.dialog.update_data_vals(vmin, vmax, spacing)

    def is_simple_contour(self):
        """
        Check to see if settings are simple enough
        to use `contour(arr, **settings.options)?`
        """
        is_simple = True
        if self.vmax is not None:
            is_simple = False
        elif self.vmin is not None:
            is_simple = False
        elif self.spacing is not None:
            is_simple = False
        return is_simple
