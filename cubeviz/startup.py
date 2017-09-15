from __future__ import print_function, division

from glue.config import startup_action
from .listener import CubevizManager


_manager = None


@startup_action('cubeviz')
def cubeviz_setup(session, data_collection):
    global _manager
    _manager = CubevizManager(session)
