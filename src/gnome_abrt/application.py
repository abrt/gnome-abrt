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
from urllib.parse import urlparse

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

    ret = (os.path.basename(executable) == os.path.basename(dexec)
            or executable == dexec
            or (realpath and compare_executable(realpath, desktop_entry)))

    if ret:
        logging.debug("executable matches Executable key: {0} == {1}"
                .format(executable, dexec))

    return ret

def _is_it_url(text):
    # URL must have scheme
    try:
        url = urlparse(text)
        return bool(url.scheme)
    #pylint: disable=W0703
    except Exception as ex:
        logging.debug(str(ex))
        return False

def _is_it_file_arg(text):
    # every string without '-' prefix could be
    # a path to file (at least relative)
    return not text.startswith('-')

def compare_cmdline(cmdline, desktop_entry):
    def _compare(cmdargs, dcmdargs):
    # http://standards.freedesktop.org/desktop-entry-spec/latest/ar01s06.html
        if not dcmdargs or not cmdargs or len(dcmdargs) > len(cmdargs):
            return False

        if os.path.basename(dcmdargs[0]) != os.path.basename(cmdargs[0]):
            return False

        cargi = 1
        dargi = 1
        while dargi < len(dcmdargs):
            if dcmdargs[dargi] == "%f":
                if cargi >= len(cmdargs) or _is_it_file_arg(cmdargs[cargi]):
                    return False
                else:
                    dargi += 1
                    cargi += 1
            elif dcmdargs[dargi] == "%F":
                if cargi >= len(cmdargs) or _is_it_file_arg(cmdargs[cargi]):
                    dargi += 1
                else:
                    cargi += 1
            elif dcmdargs[dargi] == "%u":
                if cargi >= len(cmdargs) or (not _is_it_url(cmdargs[cargi])
                        and not _is_it_file_arg(cmdargs[cargi])):
                    return False
                else:
                    cargi += 1
                    dargi += 1
            elif dcmdargs[dargi] == "%U":
                if cargi >= len(cmdargs) or (not _is_it_url(cmdargs[cargi])
                        and not _is_it_file_arg(cmdargs[cargi])):
                    dargi += 1
                else:
                    cargi += 1
            elif dcmdargs[dargi] == "%i":
                logging.debug("Unsupported Exec key %i")
                dargi += 1
                cargi += 2
            elif dcmdargs[dargi] == "%c":
                logging.debug("Unsupported Exec key %c")
                dargi += 1
                cargi += 1
            elif dcmdargs[dargi] == "%k":
                logging.debug("Unsupported Exec key %k")
                dargi += 1
                cargi += 1
            else:
                if cargi >= len(cmdargs) or dcmdargs[dargi] != cmdargs[cargi]:
                    return False
                dargi += 1
                cargi += 1

        ret = cargi == len(cmdargs) and dargi == len(dcmdargs)

        if ret:
            logging.debug("cmdline matches Exec: {0} == {1}"
                    .format(" ".join(cmdargs), " ".join(dcmdargs)))

        return ret


    if not cmdline:
        return False

    dcmdline = desktop_entry.get_commandline()
    if not dcmdline:
        return False

    if cmdline == dcmdline:
        return True

    # - cmdline consists of DBusString instances
    # - normalize by removing '"' (--foo="blah" == --foo=blah)
    # - the if condition is necessary because a pair of spaces ('  ')
    #   generates None
    cmdargs = [str(x).replace('"', '') for x in cmdline.split(" ") if x]
    dcmdargs = [str(x).replace('"', '') for x in dcmdline.split(" ") if x]

    if _compare(cmdargs, dcmdargs):
        return True

    # try to handle interpreters like python
    return len(cmdargs) > 1 and _compare(cmdargs[1:], dcmdargs)

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

    app = None
    app_last_chance = None
    # no cache entry was found, try to find corresponding desktop entry
    for pred in lookupnames:
        if not pred[0]:
            continue

        theme = Gtk.IconTheme.get_default()
        for dai in Gio.DesktopAppInfo.get_all():
            if pred[1](pred[0], dai):
                logging.debug("Found Desktop: {1} == {0}"
                        .format(cmdline, dai.get_name()))

                icon = None
                dai_icon = dai.get_icon()
                if dai_icon:
                    if isinstance(dai_icon, Gio.ThemedIcon):
                        for name in dai_icon.get_names():
                            try:
                                icon = theme.load_icon(name,
                                        128, Gtk.IconLookupFlags.USE_BUILTIN)
                                break
                            #pylint: disable=E0712
                            except GLib.GError as ex:
                                logging.debug(ex)
                    elif isinstance(dai_icon, Gio.FileIcon):
                        try:
                            stream = dai_icon.load(128, None)
                            icon = GdkPixbuf.Pixbuf.new_from_stream(stream[0],
                                                                    None)
                        #pylint: disable=E0712
                        except GLib.GError as ex:
                            logging.debug(ex)
                    else:
                        logging.debug("Unsupported type of icon class: {0}"
                                .format(dai_icon))

                if dai.get_nodisplay():
                    # remember the first hit which is the most accurate one
                    if app_last_chance is None:
                        app_last_chance = Application(executable,
                            name=dai.get_name(), icon=icon)
                else:
                    app = Application(executable,
                            name=dai.get_name(), icon=icon)
                    break

        if app is not None:
            break

    if app is None:
        if app_last_chance is not None:
            app = app_last_chance
        else:
            app = Application(executable, name=component)

    # cache by cmdline because package and component can provide many
    # applications but cmdline looks like pretty unique information
    # must not cache byt executable because of pluginable applications like
    # gnome-control-center, epiphany, ...
    if cmdline:
        __globa_app_cache__[cmdline] = app

    return app
