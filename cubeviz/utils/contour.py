import os
import matplotlib.cm as cm

from qtpy.QtWidgets import (QLabel, QAction, QActionGroup,
                            QDialog, QHBoxLayout, QVBoxLayout,
                            QPushButton, QCheckBox, QLineEdit,
                            QSpacerItem, QMessageBox)
from qtpy.QtCore import Qt

from glue.config import viewer_tool
from glue.config import colormaps as glue_colormaps
from glue.utils.qt import QColormapCombo

from glue.viewers.common.qt.tool import Tool

DEFAULT_GLUE_COLORMAP_INDEX = 3

@viewer_tool
class ContourButton(Tool):
    icon = os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        ),
        "data",
        "qt",
        "resources",
        "contour_icon.png")
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

        action = QAction("Custom Component", self.tool_bar, checkable=True)
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
    def __init__(self, contour_settings):
        super(ContourOptionsDialog, self).__init__(contour_settings.cubeviz_layout)
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.setWindowTitle("Contour Options")

        self.is_preview_active = False

        self.contour_settings = contour_settings
        self.options = self.contour_settings.options

        self._colormap_members = self.contour_settings.colormap_members
        self._colormap_index = DEFAULT_GLUE_COLORMAP_INDEX
        if "cmap" in self.options:
            if self.options["cmap"] in self._colormap_members:
                self._colormap_index = self._colormap_members.index(self.options["cmap"])

        if self.contour_settings.spacing is None:
            self.is_custom_spacing = False
        else:
            self.is_custom_spacing = True

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

        # Gap:
        self.gap = QLabel("")
        hblgap = QHBoxLayout()
        hblgap.addWidget(self.gap)

        # Line 2: Custom Contour Spacing
        self.custom_spacing_checkBox = QCheckBox("Custom Contour Spacing")
        if self.is_custom_spacing:
            self.custom_spacing_checkBox.setChecked(self.is_custom_spacing)
        self.custom_spacing_checkBox.toggled.connect(self.custom_spacing)

        hbl2 = QHBoxLayout()
        hbl2.addWidget(self.custom_spacing_checkBox)

        # Line 3: Contour Spacing
        self.spacing_label = QLabel("Contour Spacing: ")
        self.spacing_label.setDisabled(not self.is_custom_spacing)

        self.spacing_input = QLineEdit()
        self.spacing_input.setDisabled(not self.is_custom_spacing)
        if self.is_custom_spacing:
            self.spacing_input.setText(str(self.contour_settings.spacing))

        hbl3 = QHBoxLayout()
        hbl3.addWidget(self.spacing_label)
        hbl3.addWidget(self.spacing_input)

        # Line f:
        self.defaultButton = QPushButton("Default")
        self.defaultButton.clicked.connect(self.default)

        self.previewButton = QPushButton("Preview")
        self.previewButton.clicked.connect(self.preview)

        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.finish)
        self.okButton.setDefault(True)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel)

        hblf = QHBoxLayout()
        hblf.addStretch(1)
        # hblf.addWidget(self.defaultButton)
        hblf.addWidget(self.previewButton)
        hblf.addWidget(self.cancelButton)
        hblf.addWidget(self.okButton)

        vbl = QVBoxLayout()
        vbl.addLayout(hbl1)
        vbl.addLayout(hblgap)
        vbl.addLayout(hbl2)
        vbl.addLayout(hbl3)
        vbl.addLayout(hblf)

        self.setLayout(vbl)

        self.show()

    def _on_colormap_change(self, index):
        self._colormap_index = index

    def custom_spacing(self):
        if self.is_custom_spacing:
            self.is_custom_spacing = False
            self.spacing_input.setDisabled(True)
            self.spacing_label.setDisabled(True)
            self.spacing_input.setText("")
            self.spacing_input.setStyleSheet("")
        else:
            self.is_custom_spacing = True
            self.spacing_input.setDisabled(False)
            self.spacing_label.setDisabled(False)

    def input_validation(self):
        red = "background-color: rgba(255, 0, 0, 128);"
        success = True

        # Check 1: spacing_input
        if self.is_custom_spacing:
            if self.spacing_input == "":
                self.spacing_input.setStyleSheet(red)
                success = False
            else:
                try:
                    spacing = float(self.spacing_input.text())
                    if spacing <= 0:
                        self.spacing_input.setStyleSheet(red)
                        success = False
                    else:
                        self.spacing_input.setStyleSheet("")
                except ValueError:
                    self.spacing_input.setStyleSheet(red)
                    success = False
        return success

    def finish(self):
        success = self.input_validation()

        if not success:
            return

        # Change Color Map
        self._colormap_index = self.colormap_combo.currentIndex()
        colormap = self._colormap_members[self._colormap_index]
        self.contour_settings.options["cmap"] = colormap

        # Spacing
        if self.is_custom_spacing:
            self.contour_settings.spacing = float(self.spacing_input.text())
        else:
            self.contour_settings.spacing = None

        # Redraw contour
        if self.contour_settings.image_viewer.is_contour_active:
            self.contour_settings.draw_function()

        self.close()

    def preview(self):
        success = self.input_validation()

        if not success:
            return

        image_viewer = self.contour_settings.image_viewer
        preview_settings = ContourSettings(image_viewer)
        preview_settings.options = self.contour_settings.options.copy()
        preview_settings.spacing = self.contour_settings.spacing

        # Change Color Map
        self._colormap_index = self.colormap_combo.currentIndex()
        colormap = self._colormap_members[self._colormap_index]
        preview_settings.options["cmap"] = colormap

        # Spacing
        if self.is_custom_spacing:
            preview_settings.spacing = float(self.spacing_input.text())
        else:
            preview_settings.spacing = None

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
        self.contour_settings.options = self.contour_settings.default_options()
        self.contour_settings.spacing = None
        if self.contour_settings.image_viewer.is_contour_active:
            self.contour_settings.draw_function()
        self.close()

    def cancel(self):
        if self.contour_settings.image_viewer.is_contour_active:
            self.contour_settings.draw_function()
        self.close()

    def closeEvent(self, event):
        if self.is_preview_active:
            self.contour_settings.image_viewer.end_contour_preview()


class ContourSettings(object):
    def __init__(self, image_viewer):
        self.image_viewer = image_viewer
        self.cubeviz_layout = self.image_viewer.cubeviz_layout
        self.draw_function = self.image_viewer.draw_contour

        self.options = self.default_options()

        self.spacing = None

        self.colormap_members = [m[1] for m in glue_colormaps.members]
        self.colormap_members.append(cm.viridis)


    @staticmethod
    def default_options():
        options = {"cmap": cm.viridis}

        return options

    def options_dialog(self):
        ui = ContourOptionsDialog(self)
