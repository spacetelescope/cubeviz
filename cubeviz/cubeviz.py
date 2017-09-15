# Licensed under a 3-clause BSD style license - see LICENSE.rst
import sys

from glue.app.qt.application import GlueApplication


def setup():
    from . import data_factories
    from . import layout
    from . import startup

def main():
    app = GlueApplication()
    sys.exit(app.start())
