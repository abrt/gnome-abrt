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
from itertools import ifilter

# PyGObject
import gi
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GdkPixbuf

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

    realpath = None
    if executable[0] == '/' and os.path.islink(executable):
        realpath = os.readlink(executable)

        if realpath[0] != '/':
            realpath = os.path.abspath(os.path.join(os.path.dirname(executable), realpath))

        if realpath == executable:
            realpath = None

    return os.path.basename(executable) == os.path.basename(dexec) or executable == dexec or (realpath and compare_executable(realpath, de))

def compare_cmdline(cmdline, de):
    dcmdline = de.get_commandline()
    ret = os.path.basename(cmdline) == os.path.basename(dcmdline) or cmdline == dcmdline

    # try to handle interpreters like python
    if not ret:
        cmdargs = cmdline.split(" ");
        if len(cmdargs) > 1:
            ret = compare_executable(cmdargs[1], de)

    return ret

def compare_component(component, de):
    dicon = de.get_icon()
    if not dicon:
        return False

    if isinstance(dicon, Gio.ThemedIcon):
        return component in dicon.get_names()
    elif isinstance(dicon, Gio.FileIcon):
        logging.debug("File icon: {0}".format(dicon.to_string()))
        bf = os.path.basename(dicon.to_string())
        if component == bf:
            return True
        elif '.' in bf:
            component == bf[:bf.rindex('.')]
        else:
            return False
    else:
        logging.debug("Unsupported type of icon class: {0}".format(dicon))

    return False

def find_application(component, executable, cmdline):
    global __globa_app_cache__

    lookupnames = [(cmdline, compare_cmdline), (executable, compare_executable), (component, compare_component)]

    for n in lookupnames:
        if not n[0]:
            continue

        if n[0] in __globa_app_cache__:
            return __globa_app_cache__[n[0]]

        theme = Gtk.IconTheme.get_default()
        for dai in Gio.DesktopAppInfo.get_all():
            if n[1](n[0], dai):
                icon = None
                dai_icon = dai.get_icon()
                if dai_icon:
                    if isinstance(dai_icon, Gio.ThemedIcon):
                        for name in dai_icon.get_names():
                            try:
                                icon = theme.load_icon(name, 128, Gtk.IconLookupFlags.USE_BUILTIN)
                                break
                            except gi._glib.GError as e:
                                logging.debug(e.message)
                    elif isinstance(dai_icon, Gio.FileIcon):
                        stream = dai_icon.load(128, None)
                        icon = GdkPixbuf.Pixbuf.new_from_stream(stream[0], None)
                    else:
                        logging.debug("Unsupported type of icon class: {0}".format(dai_icon))

                __globa_app_cache__[n[0]] = Application(executable,
                                                        name=dai.get_name(),
                                                        icon=icon)
                return __globa_app_cache__[n[0]]

    return Application(executable if executable else "??", name=next(ifilter(lambda n: n, [component, executable, cmdline]), "??"))
