# Licensed under a 3-clause BSD style license - see LICENSE.rst
from .jwst import read_jwst_data_cube
from .kmos import read_kmos_data_cube
from .manga import read_manga_data_cube
from glue.core import Data
from glue.core.coordinates import coordinates_from_header
from ..listener import CUBEVIZ_LAYOUT
from ..layout import FLUX, ERROR, MASK

from os.path import basename, splitext
import yaml
import os
import glob
from astropy.io import fits
import numpy as np
from glue.config import data_factory

class DataConfiguration:

    def __init__(self, config_file):
        self._config_file = config_file

        with open(self._config_file, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)

            self._name = cfg['name']
            self._type = cfg['type']

            try:
                self._priority = int(cfg.get('priority', 0))
            except:
                self._priority = 0

            self._configuration = cfg['match']

            self._data = cfg.get('data', None)

    def matches(self, data_filename):
        print('=== Checking to see if it matches {}'.format(data_filename))
        return self.process(data_filename)

    def load_data(self, data_filename):

        print('in load_data goingt o load {}'.format(data_filename))

        hdulist = fits.open(data_filename)

        print(hdulist)

        try:
            flux_index = int(self._data['FLUX'])
        except:
            flux_index = self._data['FLUX']

        flux = hdulist[flux_index]
        flux_data = flux.data

        try:
            error_index = int(self._data['ERROR'])
        except:
            error_index = self._data['ERROR']
        var_data = hdulist[error_index].data

        if not self._data['DQ'] == 'None':
            mask_data = hdulist[self._data['DQ']].data
        else:
            mask_data = np.empty(flux_data.shape)

        label = "MaNGA data cube: {}".format(splitext(basename(data_filename))[0])

        data = Data(label=label)

        data.coords = coordinates_from_header(flux.header)
        data.meta[CUBEVIZ_LAYOUT] = self._name

        data.add_component(component=flux_data, label=FLUX)
        data.add_component(component=var_data, label=ERROR)
        data.add_component(component=mask_data, label=MASK)

        return data

    def process(self, filename):
        """
        Main call to which we pass in the file to see if it matches based
        on the criteria in the config file.

        :param filename:
        :return:
        """
        self._fits = fits.open(filename)


        # Now call the internal processing.
        matches = self._process('all', self._configuration['all'])

        if matches:
            print('File matches')
            return True
        else:
            print('File does not match')
            return False

    def _process(self, key, conditional):
        """
        Internal processing. This will get called numerous times recursively.

        :param key: The type of check we want to do
        :param conditional: The thing we are checking
        :return:
        """

        if 'all' == key:
            return self._all(conditional)
        elif 'any' == key:
            return self._any(conditional)
        elif 'equal' == key:
            return self._equal(conditional)
        elif 'startswith' == key:
            return self._startswith(conditional)
        elif 'extension_name' == key:
            return self._exists(conditional)

    #
    # Branch processing
    #

    def _all(self, conditionals):
        """
        Check all the conditionals and they must all be true for this to return true.

        :param conditionals:
        :return:
        """
        for key, conditional in conditionals.items():
            print('Checking {}'.format(key))
            ret = self._process(key, conditional)
            print('    returned {}'.format(ret))
            if not ret:
                return False
        print('_all: GOOD')
        return True

    def _any(self, conditionals):
        """
        Check each conditional and return true for the first one that matches true. Else return False

        :param conditionals:
        :return:
        """

        for key, conditional in conditionals.items():
            # process conditional
            ret = self._process(key, conditional)
            if ret:
                return ret

        return False

    #
    # Leaf processing
    #

    def _equal(self, value):
        """
        This is to check if a header_key entry has the same value as what is passed in here.

        :param value:
        :return:
        """
        print('equal {} {} {} {}'.format(value['header_key'], self._fits[0].header.get(value['header_key'], False), value['value'], self._fits[0].header.get(value['header_key'], False) == value['value']))
        return self._fits[0].header.get(value['header_key'], False) == value['value']

    def _startswith(self, value):
        """
        This is to check if a header_key entry starts with the value as what is passed in here.

        :param value:
        :return:
        """
        print('startswith {}'.format(self._fits[0].header.get(value['header_key'], '').startswith(value['value'])))
        return self._fits[0].header.get(value['header_key'], '').startswith(value['value'])

    def _extension_name(self, value):
        """
        This is to check if a header_key entry has the same value as what is passed in here.

        :param value:
        :return:
        """
        print('{} is an extension {}'.format(value, value in self._fits))
        return value in self._fits



class DataFactoryConfiguration:

    def __init__(self, config_files_or_directory):
        """
        The IFC takes either a directory (that contains YAML files), a list of directories (each of which contain
        YAML files) or a list of YAML files.  Each YAML file defines requirements

        :param config_files_or_directory: Directory, list of directories, or list of files.
        """

        if os.path.isdir(config_files_or_directory):
            # Get all the yaml files in the directory
            self._config_files = glob.glob(os.path.join(config_files_or_directory, '*.yaml'))
        else:
            self._config_files = config_files_or_directory

            if not isinstance(self._config_files, list):
                self._config_files = [self._config_files]

        print('DataFactorConfiguraiton:__init__:  self._config_files is {}'.format(self._config_files))

        for config_file in self._config_files:
            print('\n-----------------------------')

            print('Loading configuration file {}'.format(config_file))
            with open(config_file, 'r') as yamlfile:
                cfg = yaml.load(yamlfile)

            print('Read in {}'.format(cfg))
            name = cfg['name']
            type = cfg['type']

            try:
                priority = int(cfg.get('priority', 0))
            except:
                priority = 0

            print('Creating wrapper {}'.format(name))

            dc = DataConfiguration(config_file)
            wrapper = data_factory(name, dc.matches, priority=priority)

            print('Calling wrapper function')
            wrapper(dc.load_data)

            print('Done calling wrapper function')


