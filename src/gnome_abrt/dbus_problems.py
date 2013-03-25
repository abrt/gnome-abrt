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
import dbus
from dbus.mainloop.glib import DBusGMainLoop

import logging

import gnome_abrt.problems as problems
import gnome_abrt.config as config
import gnome_abrt.errors as errors
from gnome_abrt.l10n import _

BUS_NAME = 'org.freedesktop.problems'
BUS_PATH = '/org/freedesktop/problems'
BUS_IFACE = 'org.freedesktop.problems'

ABRTD_DBUS_PATH = '/org/freedesktop/problems'
ABRTD_DBUS_SIGNAL = 'Crash'

class DBusProblemSource(problems.CachedSource):

    def __init__(self, mainloop=None):
        super(DBusProblemSource, self).__init__()

        self._mainloop = mainloop
        if not self._mainloop:
            self._mainloop = DBusGMainLoop()

        self._bus = None
        self._proxy = None
        self._interface = None
        self._connect_to_problems_bus()

        try:
            self._bus.add_signal_receiver(self._on_new_problem,
                    signal_name=ABRTD_DBUS_SIGNAL, path=ABRTD_DBUS_PATH)
        except dbus.exceptions.DBusException as ex:
            logging.warning(
        _("Can't add receiver of signal '{0}'on DBus system path '{1}': {2}")
                      .format(ABRTD_DBUS_SIGNAL, ABRTD_DBUS_PATH, ex.message))

        class ConfigObserver():
            def __init__(self, source):
                self.source = source

            #pylint: disable=W0613
            def option_updated(self, conf, option):
                if option == "all_problems":
                    self.source.refresh()

        conf = config.get_configuration()
        conf.set_watch("all_problems", ConfigObserver(self))

    def _connect_to_problems_bus(self):
        # I can't find any description of raised exceptions
        self._bus = dbus.SystemBus(private=True, mainloop=self._mainloop)

        try:
            self._proxy = self._bus.get_object(BUS_NAME, BUS_PATH)
        except dbus.exceptions.DBusException as ex:
            raise errors.UnavailableSource(
                    _("Can't connect to DBus system bus '{0}' path '{1}': {2}")
                        .format(BUS_NAME, BUS_PATH, ex.message))

        try:
            self._interface = dbus.Interface(self._proxy, BUS_IFACE)
        except dbus.exceptions.DBusException as ex:
            raise errors.UnavailableSource(
                _("Can't get interface '{0}' on path '{1}' in bus '{2}': {3}")
                    .format(BUS_IFACE, BUS_PATH, BUS_NAME, ex.message))

    def _close_problems_bus(self):
        self._proxy = None
        self._interface = None
        self._bus.close()
        self._bus = None

    def _send_dbus_message(self, method, *args):
        try:
            return method(self._interface, *args)
        except dbus.exceptions.DBusException as ex:
            name = ex.get_dbus_name()
            if name == "org.freedesktop.DBus.Error.ServiceUnknown":
                logging.debug("Reconnecting to dbus: {0}".format(ex.message))
                self._close_problems_bus()
                self._connect_to_problems_bus()
                return method(self._interface, *args)

            raise

    def _on_new_problem(self, *args):
        if len(args) < 2:
            logging.debug(
          "Received the new problem signal with invalid number of arguments {0}"
                    .format(args))
            return

        conf = config.get_configuration()
        if (len(args) > 2
                and int(args[2]) != os.getuid()
                and not conf['all_problems']):
            logging.debug("Received the new problem signal with different uid "
                  "'{0}' ('{1}') and the all problems option is not configured"
                     .format(args[2], os.getuid()))
            return

        if len(args) == 2 and not conf['all_problems']:
            logging.debug("Received the new problem signal without the uid "
                    "argument and the all problems option is not configured")
            return

        self.process_new_problem_id(str(args[1]))

    def chown_problem(self, problem_id):
        try:
            self._send_dbus_message(
                    #pylint: disable=W0142
                    lambda iface, *params: iface.ChownProblemDir(*params),
                    problem_id)
            return True
        except dbus.exceptions.DBusException as ex:
            logging.warning(
                    _("Can't chown problem '{0}' over DBus service: {1!s}")
                    .format(problem_id, ex.message))
            return False

    def get_items(self, problem_id, *args):
        info = {}

        if len(args) != 0:
            try:
                info = self._send_dbus_message(
                        #pylint: disable=W0142
                        lambda iface, *params: iface.GetInfo(*params),
                        problem_id, args)
            except dbus.exceptions.DBusException as ex:
                if ex.get_dbus_name() in [
                                  "org.freedesktop.problems.AuthFailure",
                                  "org.freedesktop.problems.InvalidProblemDir"]:
                    self._remove_from_cache(problem_id)
                    raise errors.InvalidProblem(problem_id, ex.message)

                logging.warning(
                        _("Can't get problem data from DBus service: {0!s}")
                            .format(ex.message))

        return info

    def _get_problems(self):
        conf = config.get_configuration()

        prblms = []

        try:
            if conf['all_problems']:
                prblms = self._send_dbus_message(
                        #pylint: disable=W0142
                        lambda iface, *args: iface.GetAllProblems(*args))
            else:
                prblms  = self._send_dbus_message(
                        #pylint: disable=W0142
                        lambda iface, *args: self._interface.GetProblems(*args))
        except dbus.exceptions.DBusException as ex:
            logging.warning(
                    _("Can't get list of problems from DBus service: {0!s}")
                        .format(ex.message))

        return (str(pid) for pid in prblms)

    def _delete_problem(self, problem_id):
        try:
            self._send_dbus_message(
                #pylint: disable=W0142
                lambda iface, *args: iface.DeleteProblem(*args), [problem_id])
            return True
        except dbus.exceptions.DBusException as ex:
            if ex.get_dbus_name() in ["org.freedesktop.problems.AuthFailure",
                                "org.freedesktop.problems.InvalidProblemDir"]:
                self._remove_from_cache(problem_id)
                raise errors.InvalidProblem(problem_id, ex.message)

            logging.warning(
                    _("Can't delete problem over DBus service: {0!s}")
                        .format(ex.message))
            return False
