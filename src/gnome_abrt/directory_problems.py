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

import os
import sys
import logging

# pygobject
from gi.repository import GLib

# pyinotify
import pyinotify
from pyinotify import WatchManager, Notifier, ProcessEvent

# libreport-python
import report

# gnome-abrt
import problems
import errors
from l10n import _

class INOTIFYGlibSource(GLib.Source):

    def __new__(cls, wm, path, handler):
        # ignore the rest of arguments
        return super(INOTIFYGlibSource, cls).__new__(cls)

    def __init__(self, wm, path, handler):
        super(INOTIFYGlibSource, self).__init__()

        self.wm = wm
        self.handler = handler
        # set timeout to 0 -> don't wait
        self.notifier = Notifier(self.wm, handler, timeout=0)
        self.wdd = self.wm.add_watch(path, handler.MASK, rec=True)

    def get_handler(self):
        return self.handler

    def prepare(self, *args):
        # wait 10 milisecond before next prepare() call
        return (self.notifier.check_events(), 10)

    def check(self, *args):
        # just to be sure
        return self.notifier.check_events()

    def dispatch(self, *args):
        self.notifier.read_events()
        self.notifier.process_events()
        return True

    def finalize(self, *args):
        self.notifier.stop()


class INOTIFYProblemHandler(ProcessEvent):
    MASK = pyinotify.IN_MOVED_TO | pyinotify.IN_CLOSE_WRITE | pyinotify.IN_CREATE | pyinotify.IN_DELETE | pyinotify.IN_MOVED_FROM

    def __init__(self, problem):
        super(INOTIFYProblemHandler, self).__init__()
        self.set_problem(problem)

    def set_problem(self, problem):
        self.problem = problem

    def _handle_event(self, event):
        if event.name != '.lock':
            try:
                self.problem.refresh()
            except errors.InvalidProblem as e:
                logging.debug(e.message)
                self.problem.delete()

    def process_IN_MOVED_TO(self, event):
        logging.debug("IN_MOVED_TO '{0}/{1}'".format(event.path, event.name))
        self._handle_event(event)

    def process_IN_MOVED_FROM(self, event):
        logging.debug("IN_MOVED_FROM '{0}/{1}'".format(event.path, event.name))
        self._handle_event(event)

    def process_IN_CLOSE_WRITE(self, event):
        logging.debug("IN_CLOSE_WRITE '{0}/{1}'".format(event.path, event.name))
        self._handle_event(event)

    def process_IN_CREATE(self, event):
        logging.debug("IN_CREATE '{0}/{1}'".format(event.path, event.name))
        self._handle_event(event)

    def process_IN_DELETE(self, event):
        logging.debug("IN_DELETE '{0}/{1}'".format(event.path, event.name))
        self._handle_event(event)


class INOTIFYSourceHandler(ProcessEvent):
    MASK = pyinotify.IN_MOVED_TO

    def __init__(self, source):
        super(INOTIFYSourceHandler, self).__init__()
        self.source = source

    def process_IN_MOVED_TO(self, event):
        self.source.process_new_problem_id(os.path.join(event.path, event.name))


class INOTIFYWatcher:

    def __init__(self, source, directory, context):
        # context is the instance variable because the source is to be used in Problems
        self._source = source
        self._directory = directory
        self._context = context
        self._disabled = False

        if self._context:
            self._problems_watcher = {}

            self._wm = WatchManager()
            try:
                self._gsource = INOTIFYGlibSource(self._wm, self._directory, INOTIFYSourceHandler(self._source))
            except OSError as ex:
                self._disable_on_max_watches(ex, self._directory)
                return

            self._gsource.attach(self._context)

    def watch_problem(self, problem):
        if self._disabled:
            return

        if problem.problem_id in self._problems_watcher:
            logging.debug("Updating watcher for '{0}'".format(problem.problem_id))
            self._problems_watcher[problem.problem_id].get_handler().set_problem(problem)
        else:
            logging.debug("Adding watcher for '{0}'".format(problem.problem_id))
            pgs = None
            try:
                pgs = INOTIFYGlibSource(WatchManager(), problem.problem_id, INOTIFYProblemHandler(problem))
            except OSError as ex:
                self._disable_on_max_watches(ex, problem.problem_id)
                return

            pgs.attach(self._context)
            self._problems_watcher[problem.problem_id] = pgs

    def unwatch_problem(self, problem_id):
        if not self._disabled:
            return

        if problem_id in self._problems_watcher:
            pgs = self._problems_watcher[problem_id]
            del self._problems_watcher[problem_id]
            pgs.destroy()

    def _disable_on_max_watches(self, ex, directory):
            self._disabled = True
            logging.debug("Could not add inotify for directory '{0}': '{1}'".format(directory, ex.message))
            logging.warning(_("You have probably reached inotify's limit on the number of watches in '{0}'. The limit can be increased by proper configuration of inotify. For more details see man inotify(7). This event causes that you will not be notified about changes in problem data happening outside of this application. This event do not affect any other functionality.").format(self._directory))

class NotInitializedDirectorySource():

    def __init__(self, parent):
        self._parent = parent

    def get_items(self, problem_id, *args):
        logging.debug("Getting items from unitialized directory source")
        return

    def get_problems(self):
        return []

    def create_new_problem(self, problem_id):
        logging.debug("Creating a problem from unitialized directory source")
        return problems.Problem(problem_id, self._parent)

    def delete_problem(self, problem_id):
        logging.debug("Deleting problem from unitialized directory source")
        return True


class InitializedDirectoryProblemSource():

    def __init__(self, parent, directory, context=None):
        self._parent = parent
        self.directory = directory
        self._watcher = INOTIFYWatcher(self._parent, self.directory, context)

    def get_items(self, problem_id, *args):
        if len(args) == 0:
            return {}

        dd = report.dd_opendir(problem_id, report.DD_OPEN_READONLY)
        if not dd:
            raise errors.InvalidProblem(_("Can't open directory: '{0}'").format(problem_id))

        items = {}
        for field_name in args:
            value = dd.load_text(field_name, report.DD_FAIL_QUIETLY_ENOENT
                                              | report.DD_LOAD_TEXT_RETURN_NULL_ON_FAILURE)
            if value:
                items[field_name] = value

        dd.close()

        return items

    def get_problems(self):
        for dir_entry in os.listdir(self.directory):
            problem_id = os.path.join(self.directory, dir_entry)
            if os.path.isdir(problem_id):
                dd = report.dd_opendir(problem_id)
                if dd == None:
                    logging.debug("Omitted dir: '{0}'".format(problem_id))
                else:
                    logging.debug("Found dump dir: '{0}'".format(problem_id))
                    dd.close()
                    yield problem_id
            else:
                logging.debug("Omitted path: '{0}'".format(problem_id))

    def create_new_problem(self, problem_id):
        p = problems.Problem(problem_id, self._parent)
        self._watcher.watch_problem(p)
        return p

    def delete_problem(self, problem_id):
        dd = report.dd_opendir(problem_id)
        if not dd:
            # we can safely declare problem as deleted if directory doesn't exist
            return not os.path.isdir(problem_id)

        # TODO : delete over abrtd
        dd.delete()
        self._watcher.unwatch_problem(problem_id)
        # dd.close()
        return True


class DirectoryProblemSource(problems.CachedSource):

    def __init__(self, directory, context=None):
        super(DirectoryProblemSource, self).__init__()

        self._directory = directory
        self._context = context
        self._initialized = None
        self._notinitialized = NotInitializedDirectorySource(self)
        self._impl()

    def _impl(self):
        if self._initialized or os.path.isdir(self._directory):

            if not self._initialized:
                self._initialized = InitializedDirectoryProblemSource(self, self._directory, self._context)

            return self._initialized

        return self._notinitialized

    def chown_problem(self, problem_id):
        return True

    def get_items(self, problem_id, *args):
        return self._impl().get_items(problem_id, *args)

    def create_new_problem(self, problem_id):
        return self._impl().create_new_problem(problem_id)

    def impl_get_problems(self):
        return self._impl().get_problems()

    def impl_delete_problem(self, problem_id):
        return self._impl().delete_problem(problem_id)
