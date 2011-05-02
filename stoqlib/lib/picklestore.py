# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2011 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
## Author(s): Stoq Team <stoq-devel@async.com.br>
##
"""Utils for working with pickle files"""

import errno
import cPickle
import os
import shutil
import tempfile

from stoqlib.exceptions import PickleStoreError

class PickleStore(object):
    """A class for (re)storing pickles."""

    def __init__(self, directory, filename):
        """Creates a new PickleStore object.

        @param directory: the directory that the pickle will be saved/loaded.
        @param filename: the name of the file on the directory.
        """
        self._filename = filename
        try:
            if not os.path.exists(directory):
                os.mkdir(directory, 0755)
            self._directory = directory
        except OSError as e:
            if e.errno != errno.EPERM:
                raise PickleStoreError
            self._directory = None

    #
    #  Public API
    #

    def store(self, data):
        """Store an object in a file using pickle.

        @param data: the object that will be pickled.
        """
        if not self._directory:
            return

        tmp_fd, tmp_filename = tempfile.mkstemp(prefix='stoqlib-cache-')
        try:
            cPickle.dump(data, os.fdopen(tmp_fd, 'w'))
        except IOError as e:
            # No space left on device
            if e.errno == errno.ENOSPC:
                self._remove_filename(tmp_filename)
                return
            else:
                raise PickleStoreError

        try:
            shutil.move(tmp_filename, self._get_full_file_path())
        except IOError as e:
            # Permission denied
            if e.errno == errno.EACCES:
                self._remove_filename(tmp_filename)
            else:
                raise PickleStoreError

    def load(self):
        """Unpickle a file, returning the object in it, unpickled

        @returns: the object unpickled.
        """
        if not self._directory:
            return

        try:
            fd = open(self._get_full_file_path())
        except IOError as e:
            if e.errno == errno.ENOENT:
                return
            else:
                raise PickleStoreError

        try:
            data = cPickle.load(fd)
        except (AttributeError, EOFError, ValueError, cPickle.BadPickleGet):
            # Broken pickle entry, remove it
            self.remove()
            data = None

        return data

    def clear(self):
        """Remove the pickle file from the system"""
        if not self._directory:
            return

        self._remove_filename(self._get_full_file_path())

    #
    #  Private API
    #

    def _get_full_file_path(self):
        return os.path.join(self._directory, self._filename)

    def _remove_filename(self, filename):
        try:
            os.unlink(filename)
        except IOError, e:
            # Permission denied
            if e.errno == errno.EACCES:
                return
            else:
                raise PickleStoreError
        except OSError, e:
            # File does not exist
            if e.errno == errno.ENOENT:
                return
            else:
                raise PickleStoreError
