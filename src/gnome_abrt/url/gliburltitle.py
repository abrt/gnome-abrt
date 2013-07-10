# coding=UTF-8

## Copyright (C) 2013 ABRT team <crash-catcher@lists.fedorahosted.org>
## Copyright (C) 2013 Red Hat, Inc.

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

import sys
from Queue import Queue

# pygobject
#pylint: disable=E0611
from gi.repository import GLib

from gnome_abrt.url.urltitle import GetURLTitleThread


def get_url_title_async(url, readycallback, userdata, context=None):
    """Gets url's title assynchronously
    """

    if context is None:
        context = GLib.main_context_default()

    source = GetURLTitleThreadSource(url, readycallback, userdata)
    #pylint: disable=E1101
    source.attach(context)


class GetURLTitleThreadSource(GLib.Source):
    """Runs thread and waits until the thread does not return the url's title
    """

    #pylint: disable=W0613
    def __new__(cls, *args):
        return GLib.Source.__new__(cls)

    def __init__(self, url, readycallback, userdata):
        GLib.Source.__init__(self)

        self._queue = Queue()
        self._readycallback = readycallback
        self._userdata = userdata
        self._resolver = GetURLTitleThread(url, self._queue)
        self._resolver.start()

    def _is_ready(self):
        return not self._queue.empty()

    def prepare(self, *args):
        return (self._is_ready(), 10)

    def check(self, *args):
        return self._is_ready()

    def dispatch(self, *args):
        if not self._is_ready():
            raise RuntimeError("GetURLHTMLTitleThreadSource.dispatch()"
            " called but result is not ready yet, or already consumed.")

        # An attempty to destroy the resolver's thread ASAP
        self._resolver = None

        self._readycallback(self._queue.get(), self._userdata)

        # Destroy this source
        return False

    def finalize(self, *args):
        pass


class GetURLTitleSourcePool(object):
    """Pool for reducing number of running threads at time
    """

    def __init__(self, capacity):
        self._capacity = capacity
        self._running = 0
        self._defered = list()

    def get_url_title_async(self, url, readycallback, userdata):
        if self._running == self._capacity:
            self._defer_request(url, readycallback, userdata)
        else:
            self._start_resolving(url, readycallback, userdata)

    def _defer_request(self, url, readycallback, userdata):
        self._defered.append((url, readycallback, userdata))

    def _start_resolving(self, url, readycallback, userdata):
        self._running += 1
        get_url_title_async(url, self._resolving_done,
                (readycallback, userdata))

    def _resolving_done(self, result, userdata):
        try:
            userdata[0](result, userdata[1])
        finally:
            self._running -= 1
            if len(self._defered):
                url, readycallback, userdata = self._defered.pop()
                self._start_resolving(url, readycallback, userdata)


class GetURLTitleSourceCache(object):
    """Asynchronous cache for URL titles
    """

    def __init__(self, worker, max_size=1024):
        self._worker = worker
        self._max_size = max_size
        self._cache = dict()
        # The oldest is on the top
        self._stamp = []

    def get_url_title_async(self, url, readycallback, userdata):
        if url in self._cache:
            # Move url at the end
            self._stamp.remove(url)
            self._stamp.append(url)
            # Callers expect that result will be delivered asynchronously
            GLib.timeout_add(1,
                lambda unused: readycallback((url, self._cache[url]), userdata),
                None)
            return

        self._worker.get_url_title_async(url, self._resolved,
                                         (readycallback, userdata))

    def _resolved(self, result, userdata):
        url, title = result
        if title:
            if len(self._cache.keys()) >= self._max_size:
                # Remove the url on the top (the oldest)
                del self._cache[self._stamp.pop()]

            self._cache[url] = title
            self._stamp.append(url)

        readycallback, data = userdata
        readycallback(result, data)


if __name__ == "__main__":
    def ready(result, userdata):
        print result[1] or result[0]

        userdata["count"] = userdata["count"] - 1
        if userdata["count"] == 0:
            userdata["gloop"].quit()

    URLS = ["http://docs.python.org/2/library/htmlparser.html"]

    if len(sys.argv) > 1:
        URLS = sys.argv[1:]

    MAINLOOP = GLib.MainLoop()
    WORKER = GetURLTitleSourcePool(2)
    CONSUMER = {"count":len(URLS), "gloop":MAINLOOP}

    for u in URLS:
        WORKER.get_url_title_async(u, ready, CONSUMER)

    MAINLOOP.run()
