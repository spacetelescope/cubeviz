# Licensed under a 3-clause BSD style license - see LICENSE.rst
import sys

from glue.main import main as glue_main


def setup():
    print('IN SETUP')
    from .data_factories import DataFactoryConfiguration
    dfc = DataFactoryConfiguration('/Users/crjones/Documents/DATB/cubeviz/cubeviz/cubeviz/data_factories/configurations/')

    from . import data_factories  # noqa
    from . import layout  # noqa
    from . import startup  # noqa

from glue.main import restore_session, get_splash, load_data_files, load_plugins

def main(argv=sys.argv):

    if '--match-info' in argv:
        pass

    import glue

    from glue.utils.qt import get_qapp

    app = get_qapp()

    splash = get_splash()
    splash.show()

    # Start off by loading plugins. We need to do this before restoring
    # the session or loading the configuration since these may use existing
    # plugins.
    load_plugins(splash=splash)

    from glue.app.qt import GlueApplication

    print(argv)
    datafiles = [argv[1]]
    datafiles = datafiles or []

    hub = None

    from qtpy.QtCore import QTimer

    timer = QTimer()
    timer.setInterval(1000)
    timer.setSingleShot(True)
    timer.timeout.connect(splash.close)
    timer.start()

    gluefile = None
    if gluefile is not None:
        app = restore_session(gluefile)
        return app.start()

    config = None
    if config is not None:
        glue.env = glue.config.load_configuration(search_path=[config])

    data_collection = glue.core.DataCollection()
    hub = data_collection.hub

    splash.set_progress(100)

    session = glue.core.Session(data_collection=data_collection, hub=hub)
    ga = GlueApplication(session=session)

    if datafiles:
        datasets = load_data_files(datafiles)
        ga.add_datasets(data_collection, datasets, auto_merge=False)

    startup_actions = ['cubeviz']
    if startup_actions is not None:
        for name in startup_actions:
            ga.run_startup_action(name)

    return ga.start(maximized=True)