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
        # return 0 -> don't wait
        return (self.notifier.check_events(), 0)

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
                logging.warning(e.message)
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


class DirectoryProblemSource(problems.CachedSource):

    def __init__(self, directory, context=None):
        super(DirectoryProblemSource, self).__init__()

        if not os.path.isdir(directory):
            raise errors.UnavailableSource(_("No directory: {0}").format(directory))

        self.directory = directory
        self._problems_watcher = {}

        # context is the instance variable because the source is to be used in Problems
        self._context = context
        if self._context:
            # avoid multiple inheritance ...
            class INOTIFYHandler(ProcessEvent):
                MASK = pyinotify.IN_MOVED_TO

                def __init__(self, source):
                    super(INOTIFYHandler, self).__init__()
                    self.source = source

                def process_IN_MOVED_TO(self, event):
                    self.source.process_new_problem_id(os.path.join(event.path, event.name))

            self._wm = WatchManager()
            self._gsource = INOTIFYGlibSource(self._wm, self.directory, INOTIFYHandler(self))
            self._gsource.attach(self._context)

    def get_items(self, problem_id, *args):
        if len(args) == 0:
            return {}

        dd = report.dd_opendir(problem_id)
        if not dd:
            raise errors.InvalidProblem(_("Can't open directory: '{0}'").format(problem_id))

        items = {}
        for field_name in args:
            value = dd.load_text(field_name, 15)
            if value:
                items[field_name] = value

        dd.close()

        return items

    # overrides base implementation
    def create_new_problem(self, problem_id):
        p = problems.Problem(problem_id, self)

        if self._context:
            if problem_id in self._problems_watcher:
                logging.debug("Updating watcher for '{0}'".format(problem_id))
                self._problems_watcher[problem_id].get_handler().set_problem(p)
            else:
                logging.debug("Adding watcher for '{0}'".format(problem_id))
                pgs = INOTIFYGlibSource(WatchManager(), problem_id, INOTIFYProblemHandler(p))
                # TODO : add detach after reload ...
                pgs.attach(self._context)
                self._problems_watcher[problem_id] = pgs

        return p

    def impl_get_problems(self):
        all_problems = []

        for dir_entry in os.listdir(self.directory):
            problem_id = os.path.join(self.directory, dir_entry)
            if os.path.isdir(problem_id):
                dd = report.dd_opendir(problem_id)
                if dd:
                    dd.close()
                    yield problem_id

    def impl_delete_problem(self, problem_id):
        dd = report.dd_opendir(problem_id)
        if not dd:
            # we can safely declare problem as deleted if directory doesn't exist
            return not os.path.isdir(problem_id)

        # TODO : add detach from self._context
        # TODO : delete over abrtd
        dd.delete()
        # dd.close()
        return True
