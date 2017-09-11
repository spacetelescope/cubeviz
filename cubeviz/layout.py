from __future__ import print_function, division

from glue.config import qt_fixed_layout_tab
from qtpy.QtWidgets import QSplitter, QWidget, QVBoxLayout, QHBoxLayout
from qtpy.QtCore import Qt, QEvent, Signal
from glue.viewers.image.qt import ImageViewer
from specviz.external.glue.data_viewer import SpecVizViewer


class WidgetWrapper(QWidget):

    def __init__(self, widget=None, tab_widget=None, parent=None):
        super(WidgetWrapper, self).__init__(parent=parent)
        self.tab_widget = tab_widget
        self._widget = widget
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(widget)
        self.setLayout(self.layout)
        for child in self.children():
            if child.isWidgetType():
                child.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            self.tab_widget.subWindowActivated.emit(self)
        return super(WidgetWrapper, self).eventFilter(obj, event)

    def widget(self):
        return self._widget


@qt_fixed_layout_tab
class CubeVizLayout(QSplitter):
    """
    The 'CubeViz' layout, with three image viewers and one spectrum viewer.
    """

    LABEL = "CubeViz"
    subWindowActivated = Signal(object)

    def __init__(self, session=None, parent=None):
        super(CubeVizLayout, self).__init__(parent=parent)
        self.session = session
        self.setOrientation(Qt.Vertical)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.image1 = WidgetWrapper(ImageViewer(self.session), tab_widget=self)
        self.image2 = WidgetWrapper(ImageViewer(self.session), tab_widget=self)
        self.image3 = WidgetWrapper(ImageViewer(self.session), tab_widget=self)
        self.specviz = WidgetWrapper(SpecVizViewer(self.session), tab_widget=self)
        layout.addWidget(self.image1)
        layout.addWidget(self.image2)
        layout.addWidget(self.image3)
        widget = QWidget()
        widget.setLayout(layout)
        self.addWidget(widget)
        self.addWidget(self.specviz)
        self.subWindowActivated.connect(self._update_active_widget)

    def _update_active_widget(self, widget):
        self._active_widget = widget

    def activeSubWindow(self):
        return self._active_widget

    def subWindowList(self):
        return [self.image1, self.image2, self.image3, self.specviz]
