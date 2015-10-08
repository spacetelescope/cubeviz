def setup():

    from . import loaders
    from . import subset_ops
    from . import viewers
    from . import tools
    from . import clients

    from glue.config import qt_client
    from .qt.spectra_widget import SpectraWindow
    qt_client.add(SpectraWindow)

    from .qt.table_widget import TableWindow
    qt_client.add(TableWindow)

    from .qt.mos_widget import MOSWindow
    qt_client.add(MOSWindow)

    # from .qt.pg_widget import PGWindow
    # qt_client.add(PGWindow)
