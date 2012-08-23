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

# PyGObject
from gi.repository import Gtk
from gi.repository import Gio

class Application(object):

    def __init__(self, executable, name=None, icon=None):
        self.executable = executable

        if name:
            self.name = name
        else:
            self.name = executable

        self.icon = icon

__globa_app_cache__ = {}

def find_application(component, executable):
    global __globa_app_cache__

    if not executable in __globa_app_cache__:
        if executable and len(executable) > 0:
            lookup_exec = os.path.basename(executable)
            ll = len(lookup_exec)
            theme = Gtk.IconTheme.get_default()
            for dai in Gio.DesktopAppInfo.get_all():
                if dai.get_executable()[:ll] == lookup_exec:
                    icon = None
                    for name in dai.get_icon().get_names():
                        try:
                            icon = theme.load_icon(name, 128, Gtk.IconLookupFlags.USE_BUILTIN)
                            break
                        except gi._glib.GError as e:
                            logging.debug(e.message)

                    __globa_app_cache__[executable] = Application(executable,
                                                                  name=dai.get_name(),
                                                                  icon=icon)
                    return __globa_app_cache__[executable]
        __globa_app_cache__[executable] = Application(executable, name=component)

    return __globa_app_cache__[executable]
