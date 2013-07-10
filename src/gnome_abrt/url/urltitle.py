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
import threading
import logging
from urllib import urlopen
from HTMLParser import HTMLParser, HTMLParseError


def get_url_title(url):
    """Returns a title of the url

    Function expects that the url points to a HTML page with the title element
    in the head element. Tries to download the page and return a value of the
    title.
    """

    try:
        urlio = urlopen(url)
    except IOError as ex:
        logging.debug("{1} ('{0}')".format(url, str(ex)))
        return None

    encoding = urlio.info().getparam('charset')
    # Can't find any documentation but try except needed.
    data = urlio.read()
    if encoding:
        try:
            data = data.decode(encoding)
        except UnicodeError as ex:
            logging.debug("{1} ('{0}')".format(url, str(ex)))
            return None

    return HTMLTitleGetter.parse(data)


class HTMLTitleGetter(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)

        self._tag_head = False
        self._tag_title = False
        self._title = None

    def handle_starttag(self, tag, attrs):
        if not self._tag_head:
            self._tag_head = tag.lower() == "head"

        if self._tag_head and not self._tag_title:
            self._tag_title = tag.lower() == "title"

    def handle_endtag(self, tag):
        if self._tag_head:
            self._tag_head = tag.lower() != "head"

        if self._tag_head and self._tag_title:
            self._tag_title = tag.lower() != "title"

    def handle_data(self, data):
        if self._tag_title:
            if not self._title:
                self._title = data
            else:
                self._title += data

    @staticmethod
    def parse(data):
        tgt = HTMLTitleGetter()
        try:
            tgt.feed(data)
        except HTMLParseError as ex:
            logging.debug("{1} ('{0}')".format(data, str(ex)))
            # Hopefully title is parsed correctly

        return tgt._title


class GetURLTitleThread(threading.Thread):
    """Simple thread which puts url's title into a Queue
    """

    def __init__(self, url, que):
        super(GetURLTitleThread, self).__init__()

        self._url = url
        self._que = que

    def run(self):
        title = get_url_title(self._url)
        self._que.put((self._url, title))


if __name__ == "__main__":
    URLS = ["http://docs.python.org/2/library/htmlparser.html"]

    THREADS = False
    if len(sys.argv) > 1:
        i = 1
        if "--threads" == sys.argv[i]:
            THREADS = True
            i += 1
        URLS = sys.argv[i:]

    if THREADS:
        from Queue import Queue
        QUEUE = Queue()
        THREADS = []
        for u in URLS:
            t = GetURLTitleThread(u, QUEUE)
            t.start()
            THREADS.append(t)

        for t in THREADS:
            t.join()

        while not QUEUE.empty():
            ORIG_URL, GOT_TITLE = QUEUE.get()
            print GOT_TITLE or ORIG_URL
    else:
        for u in URLS:
            print get_url_title(u) or u
