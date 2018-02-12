

from qtpy.QtWidgets import (QLabel, QAction, QActionGroup,
                            QDialog, QHBoxLayout, QVBoxLayout,
                            QPushButton)
from qtpy.QtCore import Qt

from glue.config import viewer_tool
from glue.config import colormaps as glue_colormaps
from glue.utils.qt import QColormapCombo

from glue.viewers.common.qt.tool import Tool

DEFAULT_GLUE_COLORMAP_INDEX = 3

@viewer_tool
class ContourButton(Tool):
    icon = '/Users/rgeda/Pictures/icon.png'
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

        self.contour_settings = contour_settings
        self.options = self.contour_settings.options

        self._colormap_index = DEFAULT_GLUE_COLORMAP_INDEX
        self._init_ui()

    def _init_ui(self):
        # Line 1: Color map
        self.colormap_label = QLabel("Color Scheme: ")
        self.colormap_combo = QColormapCombo()
        self.colormap_combo.setMaximumWidth(150)
        self.colormap_combo.currentIndexChanged.connect(
            self._on_colormap_change)
        # hbl is short for Horizontal Box Layout
        hbl1 = QHBoxLayout()
        hbl1.addWidget(self.colormap_label)
        hbl1.addWidget(self.colormap_combo)

        # Line 2:
        self.defaultButton = QPushButton("Default")
        self.defaultButton.clicked.connect(self.default)

        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.finish)
        self.okButton.setDefault(True)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel)

        hbl2 = QHBoxLayout()
        hbl2.addStretch(1)
        hbl2.addWidget(self.defaultButton)
        hbl2.addWidget(self.cancelButton)
        hbl2.addWidget(self.okButton)

        vbl = QVBoxLayout()
        vbl.addLayout(hbl1)
        vbl.addLayout(hbl2)

        self.setLayout(vbl)

        self.show()

    def _on_colormap_change(self, index):
        self._colormap_index = index

    def finish(self):
        colormap = glue_colormaps.members[self._colormap_index][1]
        self.options["cmap"] = colormap
        if self.contour_settings.draw_function is not None:
            self.contour_settings.draw_function()

        self.close()

    def default(self):
        self.contour_settings.options = self.contour_settings.default_options()
        if self.contour_settings.draw_function is not None:
            self.contour_settings.draw_function()
        self.close()

    def cancel(self):
        self.close()


class ContourSettings(object):
    def __init__(self, cubeviz_layout=None, draw_function=None):
        self.options = self.default_options()
        self.cubeviz_layout = cubeviz_layout
        self.draw_function = draw_function

    @staticmethod
    def default_options():
        options = {}
        return options

    def options_dialog(self):
        ui = ContourOptionsDialog(self)