## Copyright (C) 2012 ABRT team <abrt-devel-list@redhat.com>
## Copyright (C) 2001-2005 Red Hat, Inc.

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA  02110-1335  USA

import datetime
import logging

# gnome-abrt
from gnome_abrt.application import find_application
from gnome_abrt.errors import (InvalidProblem,
                               UnavailableSource,
                               GnomeAbrtError)
from gnome_abrt.l10n import _

class ProblemSource(object):
    NEW_PROBLEM = 0
    DELETED_PROBLEM = 1
    CHANGED_PROBLEM = 2

    def __init__(self):
        self._observers = set()

    def get_items(self, problem_id, *args):
        pass

    def get_problems(self):
        pass

    def chown_problem(self, problem_id):
        pass

    def delete_problem(self, problem_id):
        pass

    def attach(self, observer):
        if not observer in self._observers:
            self._observers.add(observer)

    def detach(self, observer):
        try:
            self._observers.remove(observer)
        except ValueError as ex:
            logging.debug(ex.message)

    def notify(self, change_type=None, problem=None):
        logging.debug("{0} : Notify".format(self.__class__.__name__))
        for observer in self._observers:
            observer.changed(self, change_type, problem)

    def refresh(self):
        pass

class Problem:

    class Submission:
        URL = "URL"
        MSG = "MSG"
        BTHASH = "BTHASH"

        def __init__(self, title, rtype, data):
            self.title = title
            self.rtype = rtype
            self.data = data


    def __init__(self, problem_id, source):
        self.problem_id = problem_id
        self.source = source
        self.app = None
        self.submission = None
        self.data = self._get_initial_data(self.source)
        self._deleted = False

    def __str__(self):
        return self.problem_id

    def __eq__(self, other):
        if not other:
            return False
        elif isinstance(other, str):
            return self.problem_id == other
        elif isinstance(other, Problem):
            return self.problem_id == other.problem_id

        raise TypeError('Not allowed type in __eq__: '
                         + other.__class__.__name__)

    def __loaditems__(self, *args):
        if self._deleted:
            logging.debug("Accessing deleted problem '{0}'"
                    .format(self.problem_id))
            return {}

        items = self.source.get_items(self.problem_id, *args)
        for key, value in items.items():
            self.data[key] = value

        return items

    def __getitem__(self, item, cached=True):
        if item == 'date':
            return datetime.datetime.fromtimestamp(float(self['time']))
        elif item == 'application':
            return self.get_application()
        elif item == 'is_reported':
            return self.is_reported()
        elif item == 'submission':
            return self.get_submission()

        if cached and item in self.data:
            return self.data[item]

        loaded = self.__loaditems__(item)
        if item in loaded:
            return loaded[item]

        if item == 'count':
            return 1

        return None

    def __setitem__(self):
        raise RuntimeError("Problems are readonly")

    def __delitem__(self, item):
        raise RuntimeError("Problems are readonly")

    def __len__(self):
        return 1

    def _get_initial_data(self, source):
        return source.get_items(self.problem_id,
                                'component',
                                'executable',
                                'time',
                                'reason')

    def refresh(self):
        if self._deleted:
            logging.debug("Not refreshing deleted problem '{0}'"
                            .format(self.problem_id))
            return

        logging.debug("Refreshing problem '{0}'".format(self.problem_id))
        self.data = self._get_initial_data(self.source)
        self.submission = None
        self.source.notify(ProblemSource.CHANGED_PROBLEM, self)

    def delete(self):
        # TODO : weird?? the assignemt can be moved
        self._deleted = True
        try:
            self.source.delete_problem(self.problem_id)
        except GnomeAbrtError as ex:
            logging.warning(_("Can't delete problem '{0}': '{1}'")
                                .format(self.problem_id, ex.message))
            self._deleted = False
        except Exception as ex:
            self._deleted = False
            raise

    def is_reported(self):
        return not self['reported_to'] is None

    def assure_ownership(self):
        return self.source.chown_problem(self.problem_id)

    def get_application(self):
        if not self.app:
            self.app = find_application(self['component'],
                                        self['executable'],
                                        self['cmdline'])

        return self.app

    def get_submission(self):
        if not self.submission:
            self.submission = []
            if self['reported_to']:
                # Most common type of line in reported_to file
                # Bugzilla: URL=http://bugzilla.com/?=123456
                for line in self['reported_to'].split('\n'):
                    if len(line) == 0:
                        continue

                    pfx = []
                    i = 0
                    for i in xrange(0, len(line)):
                        if line[i] == ':':
                            break
                        pfx.append(line[i])

                    pfx = ''.join(pfx)
                    i += 1

                    for i in xrange(i, len(line)):
                        if not line[i] == ' ':
                            break

                    typ = []
                    for i in xrange(i, len(line)):
                        if line[i] == '=':
                            break
                        typ.append(line[i])

                    typ = ''.join(typ)
                    i += 1

                    self.submission.append(
                        Problem.Submission(pfx, typ, line[i:]))

        return self.submission


class MultipleSources(ProblemSource):

    def __init__(self, sources):
        super(MultipleSources, self).__init__()

        if len(sources) == 0:
            raise ValueError("At least one source must be passed")

        self.sources = sources

        class SourceObserver:
            def __init__(self, parent):
                self.parent = parent

            #pylint: disable=W0613
            def changed(self, source, change_type=None, problem=None):
                self.parent.notify(change_type, problem)

        for src in self.sources:
            src.attach(SourceObserver(self))

        self._disable_notify = False

    def get_items(self, problem_id, *args):
        pass

    def get_problems(self):
        result = []
        for src in self.sources:
            result.extend(src.get_problems())

        return result

    def chown_problem(self, problem_id):
        pass

    def delete_problem(self, problem_id):
        pass

    def notify(self, change_type=None, problem=None):
        if self._disable_notify:
            return

        super(MultipleSources, self).notify(change_type, problem)

    def refresh(self):
        self._disable_notify = True

        try:
            for src in self.sources:
                src.refresh()
        finally:
            self._disable_notify = False

        self.notify()

#pylint: disable=R0921
class CachedSource(ProblemSource):

    def __init__(self):
        super(CachedSource, self).__init__()

        self._cache = None

    def get_problems(self):
        if not self._cache:
            self._cache = []
            for prblmid in self._get_problems():
                try:
                    self._cache.append(self._create_new_problem(prblmid))
                except InvalidProblem as ex:
                    logging.warning(ex.message)
                except UnavailableSource as ex:
                    logging.warning(ex.message)

        return self._cache if self._cache else []

    def refresh(self):
        self._cache = None
        self.notify()

    def _get_problems(self):
        """Overwrite this function in ancestor"""
        raise NotImplementedError("")

    def _delete_problem(self, problem_id):
        """Overwrite this function in ancestor"""
        raise NotImplementedError("")

    def _problem_is_in_cache(self, problem_id):
        return self._cache is not None and problem_id in self._cache

    def _insert_to_cache(self, problem):
        if not self._problem_is_in_cache(problem):
            self._cache.append(problem)

    def _remove_from_cache(self, problem_id):
        if not self._problem_is_in_cache(problem_id):
            return None

        p = self._cache[self._cache.index(problem_id)]
        self._cache.remove(problem_id)
        return p

    def delete_problem(self, problem_id):
        if not self._delete_problem(problem_id):
            return

        try:
            prblm = self._remove_from_cache(problem_id)
            if prblm:
                self.notify(ProblemSource.DELETED_PROBLEM, prblm)
            return
        except ValueError as ex:
            logging.warning(_('Not found in cache but deleted: {0}'),
                    ex.message)
            self._cache = None

        self.notify()

    def _create_new_problem(self, problem_id):
        return Problem(problem_id, self)

    def process_new_problem_id(self, problem_id):
        try:
            if self._problem_is_in_cache(problem_id):
                prblm = self._cache[self._cache.index(problem_id)]
                prblm.refresh()
            else:
                prblm = self._create_new_problem(problem_id)
                self._insert_to_cache(prblm)
                self.notify(ProblemSource.NEW_PROBLEM, prblm)
        except UnavailableSource as ex:
            logging.warning(_("Source failed on processing of '{0}': {1}")
                    .format(problem_id, ex.message))
