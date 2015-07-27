from __future__ import print_function, division

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
        self.widget = None
        self.layer_data_item = None

        self.mouse_mode = self._setup_mouse_mode()

    @property
    def data(self):
        return self.client.data[0].data['cube']

    @property
    def enabled(self):
        """Return whether the window is visible and active"""
        return self.widget.isVisible()

    def close(self):
        if hasattr(self, '_mdi_wrapper'):
            self._mdi_wrapper.close()
        else:
            self.widget.close()

        self.widget = None

    def show(self):
        if self.widget.isVisible():
            return
        self.widget.show()

    def hide(self):
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
        mode = SpectrumUpdateMode(self.image_widget.client.axes,
                                  move_callback=self._move_update,
                                  press_callback=self._press_update)
        return mode

    def _get_modes(self, axes):
        return [self.mouse_mode]

    def _display_data_hook(self, data):
        pass

    def _press_update(self, mode):
        if self.widget is None:
            for viewers in self.image_widget.session.application.viewers:
                print(viewers)
                if len(viewers) > 0:
                    for l in viewers:
                        print(type(l))
                        if isinstance(l, SpectraWindow):
                            print("SpectraWindow already exists; using that.")
                            self.widget = l
                            break

        if self.widget is None:
            self.widget = SpectraWindow(self.image_widget.session)

            self.w = self.image_widget.session.application.add_widget(self)
            self.w.show()

        self.show()

    def _move_update(self, mode):
        if not mode.dragging:
            return

        x, y = mode._event_xdata, mode._event_ydata

        if self.layer_data_item is None:
            self.layer_data_item = self.widget.set_data(
                self.data.get_spectrum(x, y))
        else:
            self.widget.set_data(self.data.get_spectrum(x, y),
                                 self.layer_data_item)


class SpectrumUpdateMode(RoiMode):
    persistent = True

    def __init__(self, axes, **kwargs):
        super(SpectrumUpdateMode, self).__init__(axes, **kwargs)
        self.icon = QIcon('')
        self.mode_id = 'Spectrum Update'
        self.action_text = 'Spectrum Update'
        self.tool_tip = 'Enable live updating of spectrum'
        self._dragging = False

    def press(self, event):
        self._dragging = True
        super(SpectrumUpdateMode, self).press(event)

    def release(self, event):
        self._dragging = False
        super(SpectrumUpdateMode, self).release(event)

    @property
    def dragging(self):
        return self._dragging

    def _update_drag(self, event):
        if self._drag or self._start_event is None:
            return


class SpectrumExtractorMode(RoiMode):

    """
    Let's the user select a region in an image and,
    when connected to a SpectrumExtractorTool, uses this
    to display spectra extracted from that position
    """
    persistent = True

    def __init__(self, axes, **kwargs):
        super(SpectrumExtractorMode, self).__init__(axes, **kwargs)
        self.icon = QIcon('cube_spectrum')
        self.mode_id = 'MySpectrum'
        self.action_text = 'MySpectrum'
        self.tool_tip = 'Extract a spectrum from the selection'
        self._roi_tool = qt_roi.QtRectangularROI(self._axes)
        self._roi_tool.plot_opts.update(edgecolor='#00ff00',
                                        facecolor=None,
                                        edgewidth=3,
                                        alpha=1.0)
        self.shortcut = 'S'


# tool_registry.add(MySpectrumTool, widget_cls=ImageWidget)
tool_registry.add(SpecViewTool, widget_cls=ImageWidget)
