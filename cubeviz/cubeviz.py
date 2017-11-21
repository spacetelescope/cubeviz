# Licensed under a 3-clause BSD style license - see LICENSE.rst
import sys

from glue.main import main as glue_main


def setup():
    from . import data_factories  # noqa
    from . import layout  # noqa
    from . import startup  # noqa


def main(argv=sys.argv):

    for i in range(len(argv)):
        if argv[i].startswith('--startup'):
            if 'cubeviz' not in argv[i]:
                argv[i] = argv[i] + ',cubeviz'
            break
    else:
        argv.append('--startup=cubeviz')

    sys.exit(glue_main(argv))
