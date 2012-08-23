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
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
import signal

class Controller(object):

    def __init__(self, source):
        self.source = source
        self.run_event_fn = self._first_event_run

    def _handle_signal(self, signum):
        self.source.drop_cache()

    def report(self, problem):
        self.run_event_fn("report-gui", problem)

    def delete(self, problem):
        problem.delete()

    def detail(self, problem):
        self.run_event_fn("open-gui", problem)

    def _first_event_run(self, event, problem):
        signal.signal(signal.SIGCHLD, lambda signum, frame: self._handle_signal(signum))

        self.run_event_fn = self._run_event_on_problem
        self.run_event_fn(event, problem)

    def _run_event_on_problem(self, event, problem):
        try:
            if os.fork() == 0:
                os.execvp("/usr/libexec/abrt-handle-event", ["/usr/libexec/abrt-handle-event", "-e", event, "--", problem.problem_id])
        except OSError, e:
            print e

