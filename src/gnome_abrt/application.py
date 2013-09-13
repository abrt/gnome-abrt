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
import logging

# PyGObject
#pylint: disable=E0611
from gi.repository import GLib
#pylint: disable=E0611
from gi.repository import Gtk
#pylint: disable=E0611
from gi.repository import Gio
#pylint: disable=E0611
from gi.repository import GdkPixbuf

class Application(object):

    def __init__(self, executable, name=None, icon=None):
        self.executable = executable or "N/A"

        if name:
            self.name = name
        elif executable:
            self.name = os.path.basename(executable)
        else:
            self.name = None

        self.icon = icon


__globa_app_cache__ = {}


def compare_executable(executable, desktop_entry):
    if not executable:
        return False

    dexec = desktop_entry.get_executable()
    if not dexec:
        return False

    realpath = None
    if executable[0] == '/' and os.path.islink(executable):
        realpath = os.readlink(executable)

        if realpath[0] != '/':
            realpath = os.path.abspath(
                    os.path.join(os.path.dirname(executable), realpath))

        if realpath == executable:
            realpath = None

    return (os.path.basename(executable) == os.path.basename(dexec)
            or executable == dexec
            or (realpath and compare_executable(realpath, desktop_entry)))

def compare_cmdline(cmdline, desktop_entry):
    if not cmdline:
        return False

    ret = False
    dcmdline = desktop_entry.get_commandline()
    if dcmdline:
        ret = (os.path.basename(cmdline) == os.path.basename(dcmdline)
                or cmdline == dcmdline)

    # try to handle interpreters like python
    if not ret:
        cmdargs = [x for x in cmdline.split(" ") if x]
        if len(cmdargs) > 1:
            ret = compare_executable(cmdargs[1], desktop_entry)

    return ret

def compare_component(component, desktop_entry):
    dicon = desktop_entry.get_icon()
    if not dicon:
        return False

    if isinstance(dicon, Gio.ThemedIcon):
        names = dicon.get_names()
        if not names:
            return False
        return component in names
    elif isinstance(dicon, Gio.FileIcon):
        str_dicon = dicon.to_string()
        if not str_dicon:
            logging.debug("File icon cannot be converted to string")
            return False

        logging.debug("File icon: {0}".format(str_dicon))
        base_name = os.path.basename(str_dicon)
        if component == base_name:
            return True
        elif '.' in base_name:
            return component == base_name[:base_name.rindex('.')]
        else:
            return False
    else:
        logging.debug("Unsupported type of icon class: {0}".format(dicon))

    return False

def find_application(component, executable, cmdline):
    lookupnames = [(cmdline, compare_cmdline),
                   (executable, compare_executable),
                   (component, compare_component)]

    # explore the cache in the first step
    for pred in lookupnames:
        if not pred[0]:
            continue

        if pred[0] in __globa_app_cache__:
            return __globa_app_cache__[pred[0]]

    # no cache entry was found, try to find corresponding desktop entry
    for pred in lookupnames:
        if not pred[0]:
            continue

        theme = Gtk.IconTheme.get_default()
        for dai in Gio.DesktopAppInfo.get_all():
            if pred[1](pred[0], dai):
                icon = None
                dai_icon = dai.get_icon()
                if dai_icon:
                    if isinstance(dai_icon, Gio.ThemedIcon):
                        for name in dai_icon.get_names():
                            try:
                                icon = theme.load_icon(name,
                                        128, Gtk.IconLookupFlags.USE_BUILTIN)
                                break
                            except GLib.GError as ex:
                                logging.debug(ex)
                    elif isinstance(dai_icon, Gio.FileIcon):
                        stream = dai_icon.load(128, None)
                        icon = GdkPixbuf.Pixbuf.new_from_stream(stream[0], None)
                    else:
                        logging.debug("Unsupported type of icon class: {0}"
                                .format(dai_icon))

                __globa_app_cache__[pred[0]] = Application(executable,
                                                        name=dai.get_name(),
                                                        icon=icon)
                return __globa_app_cache__[pred[0]]

    app = Application(executable, name=component)

    # cache by cmdline because package and component can provide many
    # applications but cmdline looks like pretty unique information
    if cmdline:
        __globa_app_cache__[cmdline] = app

    return app
