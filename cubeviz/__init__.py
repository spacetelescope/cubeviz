# Licensed under a 3-clause BSD style license - see LICENSE.rst

try:
    from cubeviz.version import version as __version__
except Exception:
    # package is not installed
    __version__ = "unknown"

__all__ = ['__version__']

print('cubeviz is no longer supported, please use jdaviz. '
      'If you must use legacy cubeviz, please try v0.3 '
      'in Python 3.6.')
