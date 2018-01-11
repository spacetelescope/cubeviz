# Licensed under a 3-clause BSD style license - see LICENSE.rst
import sys
import os
import argparse

from glue.main import restore_session, get_splash, load_data_files, load_plugins

# Global variable to store the data configuration directories/files
# read in from the argparse from the command line.
# Yes, yes, we understand global variables aren't the best idea, but it
# seems to make sense here.
global_data_configuration = []

def setup():

    from .data_factories import DataFactoryConfiguration
    DataFactoryConfiguration(global_data_configuration)

    from . import layout  # noqa
    from . import startup  # noqa

def main(argv=sys.argv):
    """
    The majority of the code in this function was taken from start_glue() in main.py after a discussion with
    Tom Robataille. We wanted the ability to get command line arguments and use them in here and this seemed
    to be the cleanest way to do it.

    :param argv:
    :return:
    """

    import glue
    from glue.utils.qt import get_qapp
    app = get_qapp()

    # Splash screen
    splash = get_splash()
    splash.show()

    # Start off by loading plugins. We need to do this before restoring
    # the session or loading the configuration since these may use existing
    # plugins.
    load_plugins(splash=splash)

    from glue.app.qt import GlueApplication

    # Parse the arguments, ignore any unkonwn
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-configs", help="Directory or file for data configuration YAML files", nargs=1, type=str, action='append')
    parser.add_argument('data_files', nargs=argparse.REMAINDER)
    args = parser.parse_known_args(argv[1:])

    datafiles = args[0].data_files

    hub = None

    # Show the splash screen for 1 second
    from qtpy.QtCore import QTimer
    timer = QTimer()
    timer.setInterval(1000)
    timer.setSingleShot(True)
    timer.timeout.connect(splash.close)
    timer.start()

    # Process glue file if passed in (was an argument to start_glue()
    gluefile = None
    if gluefile is not None:
        app = restore_session(gluefile)
        return app.start()

    # Process config file if passed in (was an argument to start_glue()
    config = None
    if config is not None:
        glue.env = glue.config.load_configuration(search_path=[config])

    data_collection = glue.core.DataCollection()
    hub = data_collection.hub

    splash.set_progress(100)

    session = glue.core.Session(data_collection=data_collection, hub=hub)
    ga = GlueApplication(session=session)

    # Store the args for each ' --data-configs' found on the commandline
    global global_data_configuration
    global_data_configuration = args[0].data_configs

    # Load the data files.
    if datafiles:
        datasets = load_data_files(datafiles)
        ga.add_datasets(data_collection, datasets, auto_merge=False)

    startup_actions = ['cubeviz']
    if startup_actions is not None:
        for name in startup_actions:
            ga.run_startup_action(name)

    return ga.start(maximized=True)