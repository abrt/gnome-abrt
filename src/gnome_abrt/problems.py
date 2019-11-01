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
import re
from urllib import request

from bs4 import BeautifulSoup

import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio
gi.require_version('GLib', '2.0')
from gi.repository import GLib
gi.require_version('GObject', '2.0')
from gi.repository import GObject

# gnome-abrt
from gnome_abrt.application import find_application
from gnome_abrt.errors import (InvalidProblem,
                               UnavailableSource)

class ProblemSource:
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
        if observer not in self._observers:
            self._observers.add(observer)

    def detach(self, observer):
        try:
            self._observers.remove(observer)
        except ValueError as ex:
            logging.debug(ex)

    def notify(self, change_type=None, problem=None):
        logging.debug("{0} : Notify".format(self.__class__.__name__))
        for observer in self._observers:
            observer.changed(self, change_type, problem)

    def refresh(self):
        pass

class Problem:
    INITIAL_ELEMENTS = ['component', 'executable', 'cmdline', 'count', 'type',
                        'last_occurrence', 'time', 'reason', 'pkg_arch',
                        'pkg_epoch', 'pkg_name', 'pkg_release', 'pkg_version',
                        'environ', 'pid']

    class Submission:
        URL = "URL"
        MSG = "MSG"
        BTHASH = "BTHASH"

        def __init__(self, problem, name, rtype, data):
            self._problem = problem
            self._name = name
            self._title = name
            self._rtype = rtype
            self._data = data
            self._url_done = False

        @property
        def name(self):
            return self._name

        @property
        def rtype(self):
            return self._rtype

        @property
        def data(self):
            return self._data

        @data.setter
        def data(self, value):
            self._data = value

        @property
        def title(self):
            if self._rtype == Problem.Submission.URL and not self._url_done:
                self._url_done = True

                def on_update_title(source_object, res, user_data):
                    _, title = res.propagate_value()
                    if title:
                        self._title = title
                        self._problem.source.notify(ProblemSource.CHANGED_PROBLEM,
                                                    self._problem)

                task = Gio.Task.new(None, None, on_update_title, None)

                def update_title(task, source_object, task_data, cancellable):
                    try:
                        html = request.urlopen(self._data).read().decode("UTF-8")
                        soup = BeautifulSoup(html, "html.parser")
                        value = GObject.Value(str, soup.title.string)

                        task.return_value(value)
                    except Exception as ex:
                        error = GLib.Error("Fetching title for problem report failed: %s" % (ex))
                        task.return_error(error)

                task.run_in_thread(update_title)

            return self._title


    def __init__(self, problem_id, source):
        self.problem_id = problem_id
        self.source = source
        self.app = None
        self.submission = None
        self.data = None
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

        if self.data is None:
            self.data = {}

        items = self.source.get_items(self.problem_id, *args)
        for item in args:
            self.data[item] = items.get(item)

        return items

    #pylint: disable=R0911
    def __getitem__(self, item, cached=True):
        def datetime_from_stamp(stamp):
            try:
                return datetime.datetime.fromtimestamp(float(stamp))
            except TypeError:
                raise InvalidProblem(self.problem_id, "Empty time stamp")
            except ValueError:
                raise InvalidProblem(self.problem_id,
                                     "Invalid value in time stamp")

        if self.data is None:
            # Load initial problem data into cache
            self.__loaditems__(*Problem.INITIAL_ELEMENTS)

        if item == 'date':
            return datetime_from_stamp(self['time'])
        if item == 'date_last':
            last_ocr = self['last_occurrence']
            if last_ocr:
                return datetime_from_stamp(last_ocr)
            else:
                return datetime_from_stamp(self['time'])
        elif item == 'application':
            return self.get_application()
        elif item == 'is_reported':
            return self.is_reported()
        elif item == 'submission':
            return self.get_submission()
        elif item == 'human_type':
            return self.get_human_type()
        elif item == 'package_name':
            return self.get_package_name()
        elif item == 'package_version':
            return self.get_package_version()

        if cached and item in self.data:
            retval = self.data[item]
            if retval is None and item == "count":
                return "1"
            return retval

        loaded = self.__loaditems__(item)
        if item in loaded:
            return loaded[item]

        if item == 'count':
            return "1"

        return None

    def __setitem__(self, _, unused):
        raise RuntimeError("Problems are readonly")

    def __delitem__(self, _):
        raise RuntimeError("Problems are readonly")

    def __len__(self):
        return 1

    def refresh(self):
        if self._deleted:
            logging.debug("Not refreshing deleted problem '{0}'"
                            .format(self.problem_id))
            return

        logging.debug("Refreshing problem '{0}'".format(self.problem_id))
        self.data = None
        self.submission = None
        self.source.notify(ProblemSource.CHANGED_PROBLEM, self)

    def delete(self):
        self.source.delete_problem(self.problem_id)
        self._deleted = True

    def is_reported(self):
        return self['reported_to'] is not None

    def get_human_type(self):
        typ = self['type']

        if not typ:
            raise InvalidProblem(self.problem_id,
                    "Missing or corrupted 'type' file")

        if typ == "CCpp":
            return "C/C++"

        return typ

    def get_package_name(self):
        name = self['pkg_name']

        if not name:
            name = self['component']

        return name

    def get_package_version(self):
        epoch_value = self['pkg_epoch']

        epoch = ""
        if epoch_value and epoch_value != "0":
            epoch = "{0}:".format(epoch_value)

        version = self['pkg_version']
        release = self['pkg_release']
        arch = self['pkg_arch']

        if version and release and arch:
            return "{0}{1}-{2}.{3}".format(epoch, version, release, arch)

        return self['package']

    def assure_ownership(self):
        return self.source.chown_problem(self.problem_id)

    def get_application(self):
        if not self.app:
            self.app = find_application(self['cmdline'],
                                        self['environ'],
                                        self['pid'],
                                        self['component'])

        return self.app

    def get_submission(self):
        if not self.submission:
            reg = re.compile(r'^(?P<pfx>.*?):\s*(?P<typ>\S*?)=(?P<data>[^\s]+)')
            self.submission = []
            if self['reported_to']:
                # Most common type of line in reported_to file
                # Bugzilla: URL=http://bugzilla.com/?=123456
                for line in self['reported_to'].split('\n'):
                    if not line:
                        continue

                    parsed = reg.match(line)
                    if parsed:
                        pfx = parsed.group('pfx')
                        typ = parsed.group('typ')
                        data = parsed.group('data')
                    else:
                        continue

                    sbm = next((s for s in self.submission
                                if s.rtype == typ and s.name == pfx), None)

                    if sbm is not None:
                        sbm.data = data
                    else:
                        self.submission.append(
                            Problem.Submission(self, pfx, typ, data))

        return self.submission


class MultipleSources(ProblemSource):

    def __init__(self, sources):
        super(MultipleSources, self).__init__()

        if not sources:
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

    def __eq__(self, other):
        # override __eq__ to be able to find component source's master source
        # in a list of sources
        if isinstance(other, ProblemSource):
            # check if the other is a component
            if other in self.sources:
                return True
            elif not isinstance(other, MultipleSources):
                # the other source is not a component and cannot be self because
                # it is not an instance of MultipleSources
                return False

        # fall back to built-in behaviour (self == other)
        return NotImplemented

    def _pop_source(self, index):
        self.sources.pop(index)
        if not self.sources:
            raise UnavailableSource(self, None)

    def get_items(self, problem_id, *args):
        pass

    def _foreach_source(self, callback):
        i = 0
        while i != len(self.sources):
            try:
                callback(self.sources[i])
                i += 1
            except UnavailableSource as ex:
                logging.debug("{0}".format(str(ex)))
                if not ex.temporary:
                    self._pop_source(i)
                else:
                    i += 1

    def get_problems(self):
        result = []

        extend_result = lambda source: result.extend(source.get_problems())
        self._foreach_source(extend_result)

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
            self._foreach_source(lambda source: source.refresh())
        finally:
            self._disable_notify = False

        self.notify()

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
                    logging.warning(str(ex))

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
            return

        prblm = self._cache[self._cache.index(problem_id)]
        self._cache.remove(problem_id)
        self.notify(ProblemSource.DELETED_PROBLEM, prblm)

    def delete_problem(self, problem_id):
        if not self._delete_problem(problem_id):
            return

        try:
            self._remove_from_cache(problem_id)
        except ValueError as ex:
            logging.warning('Not found in cache but deleted: {0}'
                    .format(str(ex)))
            self._cache = None
            self.notify()

    def _create_new_problem(self, problem_id):
        return Problem(problem_id, self)

    def process_new_problem_id(self, problem_id):
        if self._problem_is_in_cache(problem_id):
            prblm = self._cache[self._cache.index(problem_id)]
            prblm.refresh()
        else:
            prblm = self._create_new_problem(problem_id)
            self._insert_to_cache(prblm)
            self.notify(ProblemSource.NEW_PROBLEM, prblm)
