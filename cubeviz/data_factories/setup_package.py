# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

def get_package_data():  # pragma: no cover
    package_name = str(_ASTROPY_PACKAGE_NAME_ + '.data_factories')
    return { package_name: ['configurations/*.yaml'] }
