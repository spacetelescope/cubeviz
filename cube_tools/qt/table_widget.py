from glue.qt.widgets.data_viewer import DataViewer
from glue.qt.widgets.table_widget import TableWidget


class TableWindow(DataViewer):

    LABEL = "Binary Table"

    def __init__(self, session, parent=None):
        super(TableWindow, self).__init__(session, parent=parent)
        self.my_widget = TableWidget(session, parent=parent)
        self.setCentralWidget(self.my_widget)
        self.my_widget.widget.setSortingEnabled(True)

    def add_data(self, data):
        self.my_widget.add_data(data)
        return True
