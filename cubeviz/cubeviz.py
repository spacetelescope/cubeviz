# Licensed under a 3-clause BSD style license - see LICENSE.rst
import sys
import os
import argparse

from qtpy.QtCore import QTimer
from qtpy import QtGui, QtWidgets

import glue
from glue.utils.qt import get_qapp
from glue.app.qt import GlueApplication
from glue.main import get_splash, load_data_files, load_plugins

try:
    from glue.utils.qt.decorators import die_on_error
except ImportError:
    from glue.utils.decorators import die_on_error

from . import __version__ as cubeviz_version
from .data_factories import DataFactoryConfiguration


CUBEVIZ_ICON_PATH = os.path.abspath(
    os.path.join(
        os.path.abspath(__file__),
        "..",
        "data",
        "resources",
        "cubeviz_icon.png"
    )
)

CUBEVIZ_LOGO_PATH = os.path.abspath(
    os.path.join(
        os.path.abspath(__file__),
        "..",
        "data",
        "resources",
        "cubeviz_logo.png"
    )
)

def setup():
    from . import layout  # noqa
    from . import startup  # noqa



def _check_datafiles_exist(datafiles):
    for fileparam in datafiles:
        for filename in fileparam.split(','):
            if not os.path.isfile(filename.strip()):
                raise IOError('The file {} does not exist'.format(filename))


def _create_glue_app(data_collection, hub):
    session = glue.core.Session(data_collection=data_collection, hub=hub)
    ga = GlueApplication(session=session)
    ga.setWindowTitle('cubeviz ({})'.format(cubeviz_version))
    qapp = QtWidgets.QApplication.instance()
    qapp.setWindowIcon(QtGui.QIcon(CUBEVIZ_ICON_PATH))
    ga.setWindowIcon(QtGui.QIcon(CUBEVIZ_ICON_PATH))
    return ga


def create_app(datafiles=[], data_configs=[], data_configs_show=False,
               interactive=True):
    """
    Create and initialize a cubeviz application instance

    Parameters
    ----------
    datafiles : `list`
        A list of filenames representing data files to be loaded
    data_configs : `list`
        A list of filenames representing data configuration files to be used
    data_configs_show : `bool`
        Display matching info about data configuration files
    interactive : `bool`
        Flag to indicate whether session is interactive or not (i.e. for testing)
    """
    app = get_qapp()

    # Splash screen
    if interactive:
        splash = get_splash()
        splash.image = QtGui.QPixmap(CUBEVIZ_LOGO_PATH)
        splash.show()
    else:
        splash = None

    # Start off by loading plugins. We need to do this before restoring
    # the session or loading the configuration since these may use existing
    # plugins.
    load_plugins(splash=splash)

    dfc_kwargs = dict(remove_defaults=True, check_ifu_valid=interactive)
    DataFactoryConfiguration(data_configs, data_configs_show, **dfc_kwargs)

    # Check to make sure each file exists and raise an Exception
    # that will show in the popup if it does not exist.
    _check_datafiles_exist(datafiles)

    # Show the splash screen for 1 second
    if interactive:
        timer = QTimer()
        timer.setInterval(1000)
        timer.setSingleShot(True)
        timer.timeout.connect(splash.close)
        timer.start()

    data_collection = glue.core.DataCollection()
    hub = data_collection.hub

    ga = _create_glue_app(data_collection, hub)
    ga.run_startup_action('cubeviz')

    # Load the data files.
    if datafiles:
        datasets = load_data_files(datafiles)
        ga.add_datasets(data_collection, datasets, auto_merge=False)

    if interactive:
        splash.set_progress(100)

    return ga


@die_on_error("Error starting up Cubeviz")
def main(argv=sys.argv):
    """
    The majority of the code in this function was taken from start_glue() in
    main.py. We wanted the ability to get command line arguments and use them
    in here and this seemed to be the cleanest way to do it.

    :param argv:
    :return:
    """

    # # Parse the arguments, ignore any unkonwn
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-configs",
        help="Directory or file for data configuration YAML files",
        action='append', default=[])
    parser.add_argument(
        "--data-configs-show", help="Show the matching info",
        action="store_true", default=False)
    parser.add_argument('data_files', nargs=argparse.REMAINDER)
    args = parser.parse_known_args(argv[1:])

    datafiles = args[0].data_files
    # Store the args for each ' --data-configs' found on the commandline
    data_configs = args[0].data_configs
    data_configs_show = args[0].data_configs_show

    app = create_app(datafiles, data_configs, data_configs_show)
    app.start(maximized=True)
