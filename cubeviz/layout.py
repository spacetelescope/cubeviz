import os
from collections import OrderedDict

import numpy as np

from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QMenu, QAction

from glue.utils.qt import load_ui
from glue.utils.qt import get_qapp
from glue.config import qt_fixed_layout_tab
from glue.external.echo import keep_in_sync, SelectionCallbackProperty
from glue.external.echo.qt import connect_combo_selection
from glue.core.data_combo_helper import ComponentIDComboHelper
from glue.core.message import SettingsChangeMessage
from glue.utils.matplotlib import freeze_margins

from specviz.third_party.glue.data_viewer import SpecVizViewer

from .toolbar import CubevizToolbar
from .image_viewer import CubevizImageViewer

from .controls.slice import SliceController
from .controls.overlay import OverlayController
from .tools import arithmetic_gui, moment_maps, smoothing

class WidgetWrapper(QtWidgets.QWidget):

    def __init__(self, widget=None, tab_widget=None, parent=None):
        super(WidgetWrapper, self).__init__(parent=parent)
        self.tab_widget = tab_widget
        self._widget = widget
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(widget)
        self.setLayout(self.layout)

    def widget(self):
        return self._widget


@qt_fixed_layout_tab
class CubeVizLayout(QtWidgets.QWidget):
    """
    The 'CubeViz' layout, with three image viewers and one spectrum viewer.
    """

    LABEL = "CubeViz"
    subWindowActivated = QtCore.Signal(object)

    single_viewer_attribute = SelectionCallbackProperty(default_index=0)
    viewer1_attribute = SelectionCallbackProperty(default_index=0)
    viewer2_attribute = SelectionCallbackProperty(default_index=1)
    viewer3_attribute = SelectionCallbackProperty(default_index=2)

    def __init__(self, session=None, parent=None):
        super(CubeVizLayout, self).__init__(parent=parent)

        if not hasattr(session.application, '_has_cubeviz_toolbar'):
            cubeviz_toolbar = CubevizToolbar(application=session.application)
            session.application.insertToolBar(session.application._data_toolbar,
                                              cubeviz_toolbar)

        self.session = session
        self._has_data = False
        self._wavelengths = None
        self._option_buttons = []

        self._data = None

        self.ui = load_ui('layout.ui', self,
                          directory=os.path.dirname(__file__))

        # Create the views and register to the hub.
        self.single_view = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.left_view = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.middle_view = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.right_view = WidgetWrapper(CubevizImageViewer(self.session), tab_widget=self)
        self.specviz = WidgetWrapper(SpecVizViewer(self.session), tab_widget=self)

        self.single_view._widget.register_to_hub(self.session.hub)
        self.left_view._widget.register_to_hub(self.session.hub)
        self.middle_view._widget.register_to_hub(self.session.hub)
        self.right_view._widget.register_to_hub(self.session.hub)
        self.specviz._widget.register_to_hub(self.session.hub)

        self.all_views = [self.single_view, self.left_view, self.middle_view, self.right_view]
        # TODO: determine whether to rename this or get rid of it
        self.cube_views = self.all_views
        self.split_views = self.cube_views[1:]

        self._synced_checkboxes = [
            self.ui.singleviewer_synced_checkbox,
            self.ui.viewer1_synced_checkbox,
            self.ui.viewer2_synced_checkbox,
            self.ui.viewer3_synced_checkbox
        ]

        for view, checkbox in zip(self.all_views, self._synced_checkboxes):
            view._widget.assign_synced_checkbox(checkbox)

        # Add the views to the layouts.
        self.ui.single_image_layout.addWidget(self.single_view)
        self.ui.image_row_layout.addWidget(self.left_view)
        self.ui.image_row_layout.addWidget(self.middle_view)
        self.ui.image_row_layout.addWidget(self.right_view)

        self.ui.specviz_layout.addWidget(self.specviz)

        self.subWindowActivated.connect(self._update_active_view)

        self.ui.sync_button.clicked.connect(self._on_sync_click)
        self.ui.button_toggle_image_mode.clicked.connect(
            self._toggle_image_mode)

        # This is a list of helpers for the viewer combo boxes. New data
        # collections should be added to each helper in this list using the
        # ``append_data`` method to ensure that the new data components are
        # populated into the combo boxes.
        self._viewer_combo_helpers = []

        # This tracks the current positions of cube viewer axes when they are hidden
        self._viewer_axes_positions = []

        # Indicates whether cube viewer toolbars are currently visible or not
        self._toolbars_visible = True

        self._slice_controller = SliceController(self)
        self._overlay_controller = OverlayController(self)

        # Add menu buttons to the cubeviz toolbar.
        self._init_menu_buttons()

        # This maps the combo box indicies to the glue data component labels
        self._component_labels = []

        self.sync = {}
        # Track the slice index of the synced viewers. This is updated by the
        # slice controller
        self.synced_index = None

        app = get_qapp()
        app.installEventFilter(self)
        self._last_click = None
        self._active_view = None
        self._active_cube = None
        self._last_active_view = None
        self._active_split_cube = None

        # Set the default to parallel image viewer
        self._single_viewer_mode = False
        self.ui.button_toggle_image_mode.setText('Single Image Viewer')
        self.ui.viewer_control_frame.setCurrentIndex(0)

    def _init_menu_buttons(self):
        """
        Add the two menu buttons to the tool bar. Currently two are defined:
            View - for changing the view of the active window
            Data Processing - for applying a data processing step to the data.

        :return:
        """
        self._option_buttons = [
            self.ui.view_option_button,
            self.ui.cube_option_button
        ]

        # Create the View Menu
        view_menu = self._dict_to_menu(OrderedDict([
            ('RA-DEC', lambda: None),
            ('RA-Spectral', lambda: None),
            ('DEC-Spectral', lambda: None),
            ('Hide Axes', ['checkable', self._toggle_viewer_axes]),
            ('Hide Toolbars', ['checkable', self._toggle_toolbars])
        ]))
        self.ui.view_option_button.setMenu(view_menu)

        # Create the Data Processing Menu
        cube_menu = self._dict_to_menu(OrderedDict([
            ('Spatial Smoothing', lambda: self._open_dialog('Spatial Smoothing', None)),
            ('Moment Maps', lambda: self._open_dialog('Moment Maps', None)),
            ('Arithmetic Operations', lambda: self._open_dialog('Arithmetic Operations', None))
        ]))
        self.ui.cube_option_button.setMenu(cube_menu)

    def _dict_to_menu(self, menu_dict):
        '''Stolen shamelessly from specviz. Thanks!'''
        menu_widget = QMenu()
        for k, v in menu_dict.items():
            if isinstance(v, dict):
                new_menu = menu_widget.addMenu(k)
                self._dict_to_menu(v, menu_widget=new_menu)
            else:
                act = QAction(k, menu_widget)

                if isinstance(v, list):
                    if v[0] == 'checkable':
                        v = v[1]
                        act.setCheckable(True)
                        act.setChecked(False)

                act.triggered.connect(v)
                menu_widget.addAction(act)
        return menu_widget

    def _handle_settings_change(self, message):
        if isinstance(message, SettingsChangeMessage):
            self._slice_controller.update_index(self.synced_index)

    def _set_pos_and_margin(self, axes, pos, marg):
        axes.set_position(pos)
        freeze_margins(axes, marg)

    def _hide_viewer_axes(self):
        for viewer in self.cube_views:
            viewer._widget.toggle_hidden_axes(True)
            axes = viewer._widget.axes
            # Save current axes position and margins so they can be restored
            pos = axes.get_position(), axes.resizer.margins
            self._viewer_axes_positions.append(pos)
            self._set_pos_and_margin(axes, [0, 0, 1, 1], [0, 0, 0, 0])
            viewer._widget.figure.canvas.draw()

    def _toggle_viewer_axes(self):
        # If axes are currently hidden, restore the original positions
        if self._viewer_axes_positions:
            for viewer, pos in zip(self.cube_views, self._viewer_axes_positions):
                viewer._widget.toggle_hidden_axes(False)
                axes = viewer._widget.axes
                self._set_pos_and_margin(axes, *pos)
                viewer._widget.figure.canvas.draw()
            self._viewer_axes_positions = []
        # Record current positions if axes are currently hidden and hide them
        else:
            self._hide_viewer_axes()

    def _toggle_toolbars(self):
        self._toolbars_visible = not self._toolbars_visible
        for viewer in self.cube_views:
            viewer._widget.toolbar.setVisible(self._toolbars_visible)

    def _open_dialog(self, name, widget):

        if name == 'Spatial Smoothing':
            ex = smoothing.SelectSmoothing(self._data, parent=self, allow_preview=True)

        if name == 'Arithmetic Operations':
            ex = arithmetic_gui.SelectArithmetic(self._data, self.session.data_collection, parent=self)

        if name == "Moment Maps":
            moment_maps.MomentMapsGUI(
                self._data, self.session.data_collection, parent=self)

    def add_new_data_component(self, name):
        self._component_labels.append(str(name))

        # TODO: udpate the active view with the new component

    def _enable_option_buttons(self):
        for button in self._option_buttons:
            button.setEnabled(True)
        self.ui.sync_button.setEnabled(True)

    def _get_change_viewer_func(self, view_index):
        def change_viewer(dropdown_index):
            view = self.all_views[view_index].widget()
            label = self._component_labels[dropdown_index]
            if view.is_smoothing_preview_active:
                view.end_smoothing_preview()
            view.update_axes_title(title=str(label))
            view.state.layers[0].attribute = self._data.id[label]
        return change_viewer

    def _enable_viewer_combo(self, data, index, combo_label, selection_label):
        print('enable_viewer_combo {} {} {}'.format(index, combo_label, selection_label))
        combo = getattr(self.ui, combo_label)
        connect_combo_selection(self, selection_label, combo)
        helper = ComponentIDComboHelper(self, selection_label)
        helper.set_multiple_data([data])
        combo.setEnabled(True)
        combo.currentIndexChanged.connect(self._get_change_viewer_func(index))
        self._viewer_combo_helpers.append(helper)

    def _enable_all_viewer_combos(self, data):
        """
        Setup the dropdown boxes that correspond to each of the left, middle,
        and right views.  The combo boxes initially are set to have FLUX,
        Error, DQ but will be dynamic depending on the type of data available
        either from being loaded in or by being processed.

        :return:
        """
        self._enable_viewer_combo(
            data, 0, 'single_viewer_combo', 'single_viewer_attribute')
        view = self.all_views[0].widget()
        view.update_axes_title(str(getattr(self, 'single_viewer_attribute')))

        for i in range(1,4):
            combo_label = 'viewer{0}_combo'.format(i)
            selection_label = 'viewer{0}_attribute'.format(i)
            self._enable_viewer_combo(data, i, combo_label, selection_label)
            view = self.all_views[i].widget()
            view.update_axes_title(str(getattr(self, selection_label)))


    def add_overlay(self, data, label):
        self._overlay_controller.add_overlay(data, label)

    def add_data(self, data):
        """
        Called by a function outside the class in order to add data to cubeviz.

        :param data:
        :return:
        """
        self._data = data
        self.specviz._widget.add_data(data)

        for checkbox in self._synced_checkboxes:
            checkbox.setEnabled(True)

        self._has_data = True
        self._active_view = self.left_view
        self._active_cube = self.left_view
        self._last_active_view = self.single_view
        self._active_split_cube = self.left_view

        # Set the component labels to what was actually in the file.
        self._component_labels = [str(x).strip() for x in data.component_ids() if not x in data.coordinate_components]

        # Store pointer to wavelength information
        self._wavelengths = self.single_view._widget._data[0].coords.world_axis(self.single_view._widget._data[0], axis=0)

        # Pass WCS and wavelength information to slider controller and enable
        wcs = self.session.data_collection.data[0].coords.wcs
        self._slice_controller.enable(wcs, self._wavelengths)

        self._enable_option_buttons()
        self._setup_syncing()

        self._enable_all_viewer_combos(data)

        self.subWindowActivated.emit(self._active_view)

    def eventFilter(self, obj, event):

        if event.type() == QtCore.QEvent.MouseButtonPress:

            if not (self.isVisible() and self.isActiveWindow()):
                return super(CubeVizLayout, self).eventFilter(obj, event)

            # Find global click position
            click_pos = event.globalPos()

            # If the click position is the same as the last one, we shouldn't
            # do anything.
            if click_pos != self._last_click:

                # Determine if the event falls inside any of the viewers
                for viewer in self.subWindowList():
                    relative_click_pos = viewer.mapFromGlobal(click_pos)
                    if viewer.rect().contains(relative_click_pos):
                        self.subWindowActivated.emit(viewer)
                        break

                self._last_click = click_pos

        return super(CubeVizLayout, self).eventFilter(obj, event)

    def _toggle_image_mode(self, event=None):
        new_active_view = self._last_active_view
        self._last_active_view = self._active_view

        # Currently in single image, moving to split image
        if self._single_viewer_mode:
            self._active_cube = self._active_split_cube
            self._activate_split_image_mode(event)
            self._single_viewer_mode = False
            self.ui.button_toggle_image_mode.setText('Single Image Viewer')
            self.ui.viewer_control_frame.setCurrentIndex(0)
            if self.single_view._widget.synced:
                for view in self.split_views:
                    if view._widget.synced:
                        view._widget.update_slice_index(self.single_view._widget.slice_index)
        # Currently in split image, moving to single image
        else:
            self._active_split_cube = self._active_cube
            self._active_view = self.single_view
            self._active_cube = self.single_view
            self._activate_single_image_mode(event)
            self._single_viewer_mode = True
            self.ui.button_toggle_image_mode.setText('Split Image Viewer')
            self.ui.viewer_control_frame.setCurrentIndex(1)

        self.subWindowActivated.emit(new_active_view)

        # Update the slice index to reflect the state of the active cube
        self._slice_controller.update_index(self._active_cube._widget.slice_index)

    def _activate_single_image_mode(self, event=None):
        vsplitter = self.ui.vertical_splitter
        hsplitter = self.ui.horizontal_splitter
        vsizes = list(vsplitter.sizes())
        hsizes = list(hsplitter.sizes())
        vsizes = 0, max(10, vsizes[0] + vsizes[1])
        hsizes = max(10, sum(hsizes) * 0.4), max(10, sum(hsizes) * 0.6)
        vsplitter.setSizes(vsizes)
        hsplitter.setSizes(hsizes)

    def _activate_split_image_mode(self, event=None):
        vsplitter = self.ui.vertical_splitter
        hsplitter = self.ui.horizontal_splitter
        vsizes = list(vsplitter.sizes())
        hsizes = list(hsplitter.sizes())
        vsizes = max(10, sum(vsizes) / 2), max(10, sum(vsizes) / 2)

        # TODO:  Might be a bug here, should the hsizes be based on vsizes? If so, not sure we need to calculate
        # TODO:  the hsizes above.
        hsizes = 0, max(10, vsizes[0] + vsizes[1])
        vsplitter.setSizes(vsizes)
        hsplitter.setSizes(hsizes)

    def _update_active_view(self, view):
        if self._has_data:
            self._active_view = view
            if isinstance(view._widget, CubevizImageViewer):
                self._active_cube = view
                index = self._active_cube._widget.slice_index
                self._slice_controller.update_index(index)

    def activeSubWindow(self):
        return self._active_view

    def subWindowList(self):
        return [self.single_view, self.left_view, self.middle_view, self.right_view, self.specviz]

    def _setup_syncing(self):
        for attribute in ['x_min', 'x_max', 'y_min', 'y_max']:
            sync1 = keep_in_sync(self.left_view._widget.state, attribute,
                                 self.middle_view._widget.state, attribute)
            sync2 = keep_in_sync(self.middle_view._widget.state, attribute,
                                 self.right_view._widget.state, attribute)
            self.sync[attribute] = sync1, sync2
        self._on_sync_click()

    def _on_sync_click(self, event=None):
        index = self._active_cube._widget.slice_index
        for view in self.cube_views:
            view._widget.synced = True
            if view != self._active_cube:
                view._widget.update_slice_index(index)
        self._slice_controller.update_index(index)

    def start_smoothing_preview(self, preview_function, component_id, preview_title=None):
        """
        Starts smoothing preview. This function preforms the following steps
        1) SelectSmoothing passes parameters.
        2) The left and single viewers' combo box is set to component_id
        3) The set_smoothing_preview is called to setup on the fly smoothing
        :param preview_function: function: Single-slice smoothing function
        :param component_id: int: Which component to preview
        :param preview_title: str: Title displayed when previewing
        """
        # For single and first viewer:
        for view_index in [0, 1]:
            view = self.all_views[view_index].widget()
            if view_index == 0:
                combo_label = 'single_viewer_combo'
            else:
                combo_label = 'viewer{0}_combo'.format(view_index)
            combo = getattr(self.ui, combo_label)
            component_index = self._component_labels.index(component_id)
            combo.setCurrentIndex(component_index)
            view.set_smoothing_preview(preview_function, preview_title)

    def end_smoothing_preview(self):
        """
        End preview and change viewer combo index to the first component.
        """
        for view_index in [0,1]:
            view = self.all_views[view_index].widget()
            view.end_smoothing_preview()
            if view_index == 0:
                combo_label = 'single_viewer_combo'
            else:
                combo_label = 'viewer{0}_combo'.format(view_index)
            combo = getattr(self.ui, combo_label)
            combo.setCurrentIndex(0)
            combo.currentIndexChanged.emit(0)

    def showEvent(self, event):
        super(CubeVizLayout, self).showEvent(event)
        # Make split image mode the default layout
        self._activate_split_image_mode()
        self._update_active_view(self.left_view)
