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

import collections

def singleton(cls):
    """
    http://www.python.org/dev/peps/pep-0318/#examples
    """
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

@singleton
class Configuration(object):

    def __init__(self):
        self.options = {}

    def set_watch(self, option, observer):
        self.options[option].observers.append(observer)

    def __getitem__(self, option):
        return self.options[option].value

    def __setitem__(self, option, value):
        opt = self.options[option]

        oldvalue = opt.value
        if oldvalue != value:
            opt.value = value
            for observer in opt.observers:
                observer.option_updated(self, option)

    def __delitem__(self, option):
        pass

    def __len__(self):
        return len(self.options)

    def get_option_value(self, option, default):
        if option in self.options:
            return self.options[option].value
        return default

    def add_option(self, short_key,
            long_key=None, description=None, default_value=None):

        if short_key in self.options:
            raise KeyError("The option already exists")

        option = collections.namedtuple('Option',
                'long_key description value observers')

        option.long_key = long_key
        option.description = description
        option.value = default_value
        option.observers = []

        self.options[short_key] = option


def get_configuration():
    return Configuration()
