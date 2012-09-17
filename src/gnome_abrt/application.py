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

# PyGObject
import gi
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


def compare_executable(executable, de):
    dexec = de.get_executable()
    return os.path.basename(executable) == os.path.basename(dexec) or executable == dexec

def compare_cmdline(cmdline, de):
    dcmdline = de.get_commandline()
    return os.path.basename(cmdline) == os.path.basename(dcmdline) or cmdline == dcmdline

def find_application(component, executable, cmdline):
    global __globa_app_cache__

    lookupnames = [(cmdline, compare_cmdline), (executable, compare_executable)]

    for n in lookupnames:
        if not n[0]:
            continue

        if n[0] in __globa_app_cache__:
            return __globa_app_cache__[executable]

        theme = Gtk.IconTheme.get_default()
        for dai in Gio.DesktopAppInfo.get_all():
            if n[1](n[0], dai):
                icon = None
                dai_icon = dai.get_icon()
                if dai_icon:
                    for name in dai_icon.get_names():
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
