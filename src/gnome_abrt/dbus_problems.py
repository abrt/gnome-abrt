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
import traceback
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

def get_standard_problems_source(mainloop=None):
    return DBusProblemSource(StandardProblems, mainloop)

def get_foreign_problems_source(mainloop=None):
    return DBusProblemSource(ForeignProblems, mainloop)

class DBusProblemSource(problems.CachedSource):

    class Driver(object):
        """Handles differences in behaviour while working with different sets
        of problems obtained from D-Bus service.
        """

        def __init__(self, source):
            self._source = source

        @property
        def get_problems_method(self):
            """Gets an instance of a method used for obtaining problems from
            D-Bus service.
            """

            raise NotImplementedError()

        def on_new_problem(self, *args):
            """Process a notification about detected problem."""

            raise NotImplementedError()

        def on_dbus_exception(self, problem_id, ex):
            """Process D-Bus errors."""

            raise NotImplementedError()


    def __init__(self, driverclass, mainloop=None):
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
                      .format(ABRTD_DBUS_SIGNAL, ABRTD_DBUS_PATH, ex))

        self._driver = driverclass(self)

    def _connect_to_problems_bus(self):
        # I can't find any description of raised exceptions
        self._bus = dbus.SystemBus(private=True, mainloop=self._mainloop)

        try:
            self._proxy = self._bus.get_object(BUS_NAME, BUS_PATH)
        except dbus.exceptions.DBusException as ex:
            raise errors.UnavailableSource(self, False,
                    _("Can't connect to DBus system bus '{0}' path '{1}': {2}")
                        .format(BUS_NAME, BUS_PATH, ex))

        try:
            self._interface = dbus.Interface(self._proxy, BUS_IFACE)
        except dbus.exceptions.DBusException as ex:
            raise errors.UnavailableSource(self, False,
                _("Can't get interface '{0}' on path '{1}' in bus '{2}': {3}")
                    .format(BUS_IFACE, BUS_PATH, BUS_NAME, ex))

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
                logging.debug("Reconnecting to dbus: {0}".format(ex))
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

        prblm_id = self._driver.on_new_problem(*args)
        if prblm_id is not None:
            self.process_new_problem_id(prblm_id)

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
                    .format(problem_id, ex))
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
                self._driver.on_dbus_exception(problem_id, ex)
                logging.warning(
                        _("Can't get problem data from DBus service: {0!s}")
                            .format(ex))

        return info

    def _get_problems(self):
        prblms = []
        try:
            prblms = self._send_dbus_message(self._driver.get_problems_method)
        except dbus.exceptions.DBusException as ex:
            logging.warning(
                    _("Can't get list of problems from DBus service: {0!s}")
                        .format(ex))

        return (str(pid) for pid in prblms)

    def _delete_problem(self, problem_id):
        try:
            self._send_dbus_message(
                #pylint: disable=W0142
                lambda iface, *args: iface.DeleteProblem(*args), [problem_id])
            return True
        except dbus.exceptions.DBusException as ex:
            self._driver.on_dbus_exception(problem_id, ex)
            logging.warning(
                    _("Can't delete problem over DBus service: {0!s}")
                        .format(ex))
            return False


class StandardProblems(DBusProblemSource.Driver):
    """The old behaviour."""

    def __init__(self, source):
        super(StandardProblems, self).__init__(source)

        class ConfigObserver(object):
            def __init__(self, source):
                self._source = source

            #pylint: disable=W0613
            def option_updated(self, conf, option):
                if option == "all_problems":
                    self._source.refresh()

        conf = config.get_configuration()
        conf.set_watch("all_problems", ConfigObserver(self._source))

    #pylint: disable=W0142
    @property
    def get_problems_method(self):
        conf = config.get_configuration()
        if conf['all_problems']:
            #pylint: disable=W0142
            return lambda iface, *args: iface.GetAllProblems(*args)
        else:
            #pylint: disable=W0142
            return lambda iface, *args: iface.GetProblems(*args)

    def on_new_problem(self, *args):
        """Accepts foreign problems only if the all_problems option is enabled
        """

        conf = config.get_configuration()
        try:
            if (len(args) > 2
                    and int(args[2]) != os.getuid()
                    and not conf['all_problems']):
                logging.debug("Received the new problem signal with different "
                              "uid '{0}' ('{1}') and the all problems option "
                              "is not configured" .format(args[2], os.getuid()))
                return None
        except ValueError:
            logging.debug(traceback.format_exc())
            return None

        if len(args) == 2 and not conf['all_problems']:
            logging.debug("Received the new problem signal without the uid "
                    "argument and the all problems option is not configured")
            return None

        return str(args[1])

    def on_dbus_exception(self, problem_id, ex):
        """Process AuthFailure error in same way as InvalidProblemDir because
        this sort of problem source provides all kinds of problems. The user
        problems which should be always accessible and the foreign problems
        which may be inaccessible when a user cancels the authentication
        dialogue. So, an AuthFailure error in this context means that a one
        of many problems is unavailable (something like an invalid problem).
        """

        if ex.get_dbus_name() in ["org.freedesktop.problems.AuthFailure",
                            "org.freedesktop.problems.InvalidProblemDir"]:
            self._source._remove_from_cache(problem_id)
            raise errors.InvalidProblem(problem_id, ex)


class ForeignProblems(DBusProblemSource.Driver):

    def __init__(self, source):
        super(ForeignProblems, self).__init__(source)

    @property
    def get_problems_method(self):
         #pylint: disable=W0142
        return lambda iface, *args: iface.GetForeignProblems(*args)

    def on_new_problem(self, *args):
        """Accepts only foreign problems."""

        args_len = len(args)
        try:
            if args_len == 2 or (args_len > 2 and int(args[2]) != os.getuid()):
                return str(args[1])
        except ValueError:
            logging.debug(traceback.format_exc())
            return None

        logging.debug("Received the new problem signal with current user's uid "
              "'{0}' ('{1}') in ForeignPorblems driver"
                 .format(args[2], os.getuid()))

        return None

    def on_dbus_exception(self, problem_id, ex):
        """If the authentication fails, a foreign problems source become
        temporary unavailable because we expect that the failure was caused by
        dismissing of the authentication dialog and all problems provided by
        this kind of source require authentication (none of them is available
        now). So, it means that a view can try to query the temporary
        unavailable source later.
        """

        if ex.get_dbus_name() == "org.freedesktop.problems.AuthFailure":
            logging.debug("User dismissed D-Bus authentication")
            raise errors.UnavailableSource(self._source, True)

        if ex.get_dbus_name() == "org.freedesktop.problems.InvalidProblemDir":
            self._source._remove_from_cache(problem_id)
            raise errors.InvalidProblem(problem_id, ex)
