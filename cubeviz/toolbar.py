from qtpy import QtWidgets


class CubevizToolbar(QtWidgets.QToolBar):

    def __init__(self, application=None, parent=None):

        super(CubevizToolbar, self).__init__(parent=parent)

        self.application = application

        self._button_viewer_options = QtWidgets.QPushButton()
        self._button_viewer_options.setText("Hide viewer options")
        self._button_viewer_options.clicked.connect(self._toggle_sidebar)

        self.addWidget(self._button_viewer_options)

    def _toggle_sidebar(self, event=None):
        splitter = self.application._ui.main_splitter
        sizes = list(splitter.sizes())
        if sizes[0] == 0:
            sizes[0] += 10
            sizes[1] -= 10
            self._button_viewer_options.setText("Hide viewer options")
        else:
            sizes[1] = sizes[0] + sizes[1]
            sizes[0] = 0
            self._button_viewer_options.setText("Show viewer options")
        splitter.setSizes(sizes)
