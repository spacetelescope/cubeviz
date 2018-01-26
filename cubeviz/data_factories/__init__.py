# Licensed under a 3-clause BSD style license - see LICENSE.rst
from os.path import basename, splitext
import yaml
import os
import glob
import logging

from glue.core import Data
from glue.core.coordinates import coordinates_from_header
from glue.config import data_factory
from astropy.io import fits
import numpy as np

from ..listener import CUBEVIZ_LAYOUT

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('cubeviz_data_configuration')
logger.setLevel(logging.INFO)

DEFAULT_DATA_CONFIGS = os.path.join(os.path.dirname(__file__), 'configurations')
CUBEVIZ_DATA_CONFIGS = 'CUBEVIZ_DATA_CONFIGS'

class DataConfiguration:
    """
    This class is used to parse a YAML configuration file.

    """

    def __init__(self, config_file):
        """
        Given the configuration file, save it and grab the name and priority
        :param config_file:
        """
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


    def load_data(self, data_filename):
        """
        Load the data based on the extensions defined in the matching YAML file.  THen
        create the datacube and return it.

        :param data_filename:
        :return:
        """
        hdulist = fits.open(data_filename)

        label = "{}: {}".format(self._name, splitext(basename(data_filename))[0])
        data = Data(label=label)

        # this attribute is used to indicate to the cubeviz layout that this is a cubeviz-specific data component.
        data.meta[CUBEVIZ_LAYOUT] = self._name

        data_coords_set = False
        for ii, hdu in enumerate(hdulist):
            if 'NAXIS' in hdu.header and hdu.header['NAXIS'] == 3:

                # Set the coords based on the first 3D HDU
                if not data_coords_set:
                    data.coords = coordinates_from_header(hdu.header)
                    data_coords_set = True

                component_name = str(ii)
                if 'EXTNAME' in hdu.header:
                    component_name = hdu.header['EXTNAME']

                    print('Adding component {}'.format(component_name))
                    data.add_component(component=hdu.data, label=component_name)


        return data

    def matches(self, filename):
        """
        Main call to which we pass in the file to see if it matches based
        on the criteria in the config file.

        :param filename:
        :return:
        """
        self._fits = fits.open(filename)

        logger.debug('Checking {} to see if matches {}'.format(filename, self._config_file))

        # Now call the internal processing.
        matches = self._process('all', self._configuration['all'])

        if matches:
            logger.debug('{} matches {}'.format(self._config_file, filename))
        else:
            logger.debug('{} does not match {}'.format(self._config_file, filename))

        return matches

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
        elif 'extension_names' == key:
            return self._extension_names(conditional)

    #
    # Branch processing
    #

    def _all(self, conditionals):
        """
        Check all the conditionals and they must all be true for this to return true.

        :param conditionals:
        :return:
        """
        logger.debug('\tall: {}'.format(conditionals))
        for key, conditional in conditionals.items():
            ret = self._process(key, conditional)
            if not ret:
                return False
        return True

    def _any(self, conditionals):
        """
        Check each conditional and return true for the first one that matches true. Else return False

        :param conditionals:
        :return:
        """

        logger.debug('\tany: {}'.format(conditionals))
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
        logger.debug('\tequality: {} = {} ?'.format(self._fits[0].header.get(value['header_key'], False), value['value']))
        return self._fits[0].header.get(value['header_key'], False) == value['value']

    def _startswith(self, value):
        """
        This is to check if a header_key entry starts with the value as what is passed in here.

        :param value:
        :return:
        """
        logger.debug('\tstartswith: {} starswith {} ?'.format(self._fits[0].header.get(value['header_key'], False), value['value']))
        return self._fits[0].header.get(value['header_key'], '').startswith(value['value'])

    def _extension_names(self, value):
        """
        This is to check if a header_key entry has the same value as what is passed in here.

        :param value:
        :return:
        """
        logger.debug('\tcontains extension: {} in {} ?'.format(value,
                                                               [x.header['EXTNAME'] for x in self._fits if 'EXTNAME' in x.header]))

        if isinstance(value, str):
            return value in self._fits
        else:
            return all([v in self._fits for v in value])



class DataFactoryConfiguration:
    """
    This class takes in lists of files or directories that are or contain data configuration YAML files. These
    can come from:
       1. the default location
       2. from the command line "--data-configs <file-or-directory>"
       3. from the environment variable CUBEVIZ_DATA_CONFIGS=<files-or-directories>
    """

    def _find_yaml_files(self, files_or_directories):
        """
        Given the files_or_directories, create a list of all relevant YAML files.

        :param files_or_directories:
        :return:
        """
        config_files = []

        # If the thing passed in was a string then we'll split on colon. If there is only one
        # directory then it will create a list anyway.
        if isinstance(files_or_directories, str):
            files_or_directories = files_or_directories.split(':')

        for x in files_or_directories:
            if os.path.exists(x):
                # file, just append
                if os.path.isfile(x):
                    config_files.append(x)
                # directory, find all yaml under it.
                else:
                    files  = glob.glob(os.path.join(x, '*.yaml'))
                    config_files.extend(files)

        return config_files

    def __init__(self, in_configs=[], show_only=False):
        """
        The IFC takes either a directory (that contains YAML files), a list of directories (each of which contain
        YAML files) or a list of YAML files.  Each YAML file defines requirements

        :param in_configs: Directory, list of directories, or list of files.
        """

        if show_only:
            logger.setLevel(logging.DEBUG)

        self._config_files = []

        # Get all the available YAML data configuration files based on the command line.
        logger.debug('YAML data configuration fiels from command line: {}'.format(in_configs))
        self._config_files.extend(self._find_yaml_files(in_configs))

        # Get all the available YAML data configuration files based on the environment variable.
        if CUBEVIZ_DATA_CONFIGS in os.environ:
            logger.debug('YAML data configuration fiels from environment variable: {}'.format(os.environ[CUBEVIZ_DATA_CONFIGS]))
            self._config_files.extend(self._find_yaml_files(os.environ[CUBEVIZ_DATA_CONFIGS]))

        # Get all the available YAML data configuration files based on the default directory
        logger.debug(
            'YAML data configuration fiels from the default directory: {}'.format(DEFAULT_DATA_CONFIGS))
        self._config_files.extend(self._find_yaml_files(DEFAULT_DATA_CONFIGS))

        logger.debug(
            'YAML data configuration files: {}'.format('\n'.join(self._config_files)))

        for config_file in self._config_files:

            # Load the YAML file and get the name, priority and create the data factory wrapper
            with open(config_file, 'r') as yamlfile:
                cfg = yaml.load(yamlfile)

            name = cfg['name']

            try:
                priority = int(cfg.get('priority', 0))
            except:
                priority = 0

            # The code below instantiates a data configuration object based on the config file and is
            # therefore dependent on the type of data file.  The data configuration object defines two functions
            # 'matches' and 'load_data' that are used.  We needed a way to call Glue's data_factory and be able
            # to pass in functions that have state information.
            dc = DataConfiguration(config_file)
            wrapper = data_factory(name, dc.matches, priority=priority)
            wrapper(dc.load_data)
