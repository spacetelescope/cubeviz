def setup():

    from . import loaders
    from . import subset_ops
    from . import viewers
    from . import tools

    from glue.config import qt_client
    from .qt.spectra_widget import SpectraWindow
    qt_client.add(SpectraWindow)