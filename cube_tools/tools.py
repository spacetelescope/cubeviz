from __future__ import print_function

from specview.external.qt import QtGui, QtCore
from glue.plugins.tools.spectrum_tool import SpectrumTool
from glue.qt.mouse_mode import RoiMode, qt_roi
from glue.config import tool_registry
from glue.qt.widgets import ImageWidget
from glue.qt.qtutil import get_icon
from glue.external.qt.QtGui import QIcon
from glue.qt.widgets.glue_mdi_area import GlueMdiSubWindow

from .qt.spectra_widget import SpectraWindow


class MySpectrumTool(SpectrumTool):
    """Just making another one"""

    def _setup_mouse_mode(self):
        print('setting up my own mouse mode')
        # This will be added to the ImageWidget's toolbar
        mode = SpectrumExtractorMode(self.image_widget.client.axes,
                                     release_callback=self._update_profile,
                                     move_callback=self._update_profile)
        return mode


class SpecViewTool(object):
    """An interface between the Glue ImageWidget and the SpecView
    SpectraWidget, facilitating instant-update of spectrum view.
    """
    def __init__(self, image_widget):
        self.image_widget = image_widget
        self.client = self.image_widget.client
        self.widget = SpectraWindow(self.image_widget.session)
        self.mouse_mode = self._setup_mouse_mode()

        w = self.image_widget.session.application.add_widget(self)
        w.close()

        pos = self.image_widget.central_widget.canvas.mapFromGlobal(
            QtGui.QCursor.pos())
        x, y = pos.x(), self.image_widget.central_widget.canvas.height() - \
               pos.y()
        print(x, y)

        info = self.client.point_details(x, y)
        print(info)

    def close(self):
        if hasattr(self, '_mdi_wrapper'):
            self._mdi_wrapper.close()
        else:
            self.widget.close()

    def mdi_wrap(self):
        sub = GlueMdiSubWindow()
        sub.setWidget(self.widget)
        self.widget.destroyed.connect(sub.close)
        sub.resize(self.widget.size())
        self._mdi_wrapper = sub
        return sub

    def _setup_mouse_mode(self):
        # This will be added to the ImageWidget's toolbar
        mode = SpectrumExtractorMode(self.image_widget.client.axes)
        return mode

    def _get_modes(self, axes):
        return [self.mouse_mode]

    def _display_data_hook(self, data):
        pass



class SpectrumExtractorMode(RoiMode):

    """
    Let's the user select a region in an image and,
    when connected to a SpectrumExtractorTool, uses this
    to display spectra extracted from that position
    """
    persistent = True

    def __init__(self, axes, **kwargs):
        super(SpectrumExtractorMode, self).__init__(axes, **kwargs)
        self.icon = QIcon('cube_spectrum.png')
        self.mode_id = 'MySpectrum'
        self.action_text = 'MySpectrum'
        self.tool_tip = 'Extract a spectrum from the selection'


# tool_registry.add(MySpectrumTool, widget_cls=ImageWidget)
# tool_registry.add(SpecViewTool, widget_cls=ImageWidget)
