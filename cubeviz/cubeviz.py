# Licensed under a 3-clause BSD style license - see LICENSE.rst
import sys

from glue.app.qt.application import GlueApplication


def setup():
    from cubeviz.utils.loader import read_jwst_data_cube

def main():
    app = GlueApplication()
    sys.exit(app.start())
