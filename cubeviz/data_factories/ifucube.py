import os
import logging

from astropy.io import fits

logging.basicConfig(level=logging.DEBUG, format="%(filename)s: %(levelname)8s %(message)s")
log = logging.getLogger('ifcube')
log.setLevel(logging.DEBUG)


class IFUCube(object):
    """
    Check and correct the IFUCube
    """

    def __init__(self):
        self._fits = None
        self._filename = None

    def open(self, filename, fix=False):
        """
        Check all checkers
        """
        self._filename = filename

        log.debug('In check with filename {} and fix {}'.format(filename, fix))

        # Check existence of the file
        if not os.path.isfile(filename):
            log.warning('File {} does not exist'.format(filename))
            return
        else:
            log.info('File {} exists'.format(filename))

        # Open the file
        try:
            self._fits = fits.open(filename)
        except:
            log.warning('Could not open {} '.format(filename))
            return

        self.check(fix)

        return self._fits

    def check(self, fix=False):
        """
        Check all checkers
        """
        log.debug('In check with filename {} and fix {}'.format(self._filename, fix))

        self.check_data(fix)

        self.check_ctype1(fix)

        self.check_ctype2(fix)

        self.check_ctype3(fix)

        return self._fits

    def check_data(self, fix=False):
        """
        Check CTYPE and make sure it is the correct value

        :param: fits_file: The open fits file
        :param: fix: boolean whether to fix it or not
        :return: boolean whether it is good or not
        """
        log.debug('In check_data')
        good = False
        data_shape = []

        for ii, hdu in enumerate(self._fits):

            # Check the EXTNAME field for this HDU
            if not 'EXTNAME' in hdu.header:
                log.warning(' HDU {} has no EXTNAME field'.format(ii))

                if fix:
                    self._fits[ii].header['EXTNAME'] = 'Extension {}'.format(ii)
                    log.info(' Setting HDU {} EXTNAME field to {}'.format(ii, self._fits[ii].header['EXTNAME']))

            if hasattr(hdu, 'data') and hdu.data is not None and len(hdu.data.shape) == 3:
                good = True
                extname = self._fits[ii].header['EXTNAME']

                log.info('  data exists in HDU ({}, {}) and is of shape {}'.format(
                    ii, extname, hdu.data.shape))

                # Check to see if the same size as the others
                if data_shape and not data_shape == hdu.data.shape:
                    log.warning('  Data are of different shapes (previous was {} and this is {})'.format(data_shape, hdu.data.shape))

                data_shape = hdu.data.shape

        if not good:
            log.error('  Can\'t fix lack of data')
            return False

        return good

    def check_ctype1(self, fix=False):
        self._check_ctype(key='CTYPE1', correct='RA--TAN', fix=fix)

    def check_ctype2(self, fix=False):
        self._check_ctype(key='CTYPE2', correct='DEC--TAN', fix=fix)

    def check_ctype3(self, fix=False):
        self._check_ctype(key='CTYPE3', correct='WAVE', fix=fix)

    def _check_ctype(self, key, correct, fix=False):
        """
        Check CTYPE1 and make sure it is the correct value

        :param: fits_file: The open fits file
        :param: fix: boolean whether to fix it or not
        :return: boolean whether it is good or not
        """
        log.debug('In check for {}'.format(key))
        good = False
        ctype = None

        # Check the first HDU which is where it is supposed to be
        if key in self._fits[0].header and not self._fits[0].header[key] == correct:
            ctype = self._fits[0].header[key]
            log.info('Good, found {}, {}, in initial header'.format(key, ctype))
            good = True

        # If not in the first HDU then check the others
        else:
            log.warning('{} not in first HDU, checking others'.format(key))
            for ii, hdu in enumerate(self._fits):
                if ii == 0 and ctype is None:
                    continue

                extname = hdu.header['EXTNAME'] if 'EXTNAME' in hdu.header else 'No extension name'

                if key in hdu.header:
                    ctype = hdu.header[key]
                    log.info('Found {} = {} in ({}, {})'.format(key, ctype, ii, extname))
                    good = True

        if not good and fix:
            ctype = correct
            log.info('{} not found and setting to {}'.format(key, ctype))

        log.info('ctype is {}'.format(ctype))

        return good
