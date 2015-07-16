from glue.plugins.tools.spectrum_tool import SpectrumTool
from glue.qt.mouse_mode import RoiMode, qt_roi
from glue.config import tool_registry
from glue.qt.widgets import ImageWidget
from glue.qt.qtutil import get_icon
from glue.external.qt.QtGui import QIcon


class MySpectrumTool(SpectrumTool):
    """Just making another one"""

    def _setup_mouse_mode(self):
        print 'setting up my own mouse mode'
        # This will be added to the ImageWidget's toolbar
        mode = SpectrumExtractorMode(self.image_widget.client.axes,
                                     release_callback=self._update_profile,
                                     move_callback=self._update_profile)
        return mode


class SpectrumExtractorMode(RoiMode):

    """
    Let's the user select a region in an image and,
    when connected to a SpectrumExtractorTool, uses this
    to display spectra extracted from that position
    """
    persistent = True

    def __init__(self, axes, **kwargs):
        super(SpectrumExtractorMode, self).__init__(axes, **kwargs)
        self.icon = QIcon('./icons/cube_spectrum')
        self.mode_id = 'MySpectrum'
        self.action_text = 'MySpectrum'
        self.tool_tip = 'Extract a spectrum from the selection'
        self._roi_tool = qt_roi.QtRectangularROI(self._axes)
        self._roi_tool.plot_opts.update(edgecolor='#00ff00',
                                        facecolor=None,
                                        edgewidth=3,
                                        alpha=1.0)
        self.shortcut = 'S'


tool_registry.add(MySpectrumTool, widget_cls=ImageWidget)
