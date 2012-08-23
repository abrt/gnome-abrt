import os
import dbus
from dbus.mainloop.glib import DBusGMainLoop

import logging

import problems
import config
import errors
from l10n import _

BUS_NAME = 'org.freedesktop.problems'
BUS_PATH = '/org/freedesktop/problems'
BUS_IFACE = 'org.freedesktop.problems'

ABRTD_DBUS_PATH = '/com/redhat/abrt'
ABRTD_DBUS_SIGNAL = 'Crash'

class DBusProblemSource(problems.CachedSource):

    def __init__(self, mainloop=None):
        super(DBusProblemSource, self).__init__()

        self._mainloop = mainloop
        if not self._mainloop:
            self._mainloop = DBusGMainLoop()

        self._connect_to_problems_bus()

        try:
            self.bus.add_signal_receiver(self._on_new_problem, signal_name=ABRTD_DBUS_SIGNAL,
                                                                      path=ABRTD_DBUS_PATH)
        except dbus.exceptions.DBusException as e:
            logging.warning(_("Can't add receiver of signal '{0}'on DBus system path '{1}': {2}")
                              .format(ABRTD_DBUS_SIGNAL, ABRTD_DBUS_PATH, e.message))

        class ConfigObserver():
            def __init__(self, source):
                self.source = source

            def option_updated(self, conf, option):
                if option == "all_problems":
                    self.source.drop_cache()

        conf = config.get_configuration()
        conf.set_watch("all_problems", ConfigObserver(self))
        self._all_problems = None

    def _connect_to_problems_bus(self):
        # I can't find any description of raised exceptions
        self.bus = dbus.SystemBus(private=True, mainloop=self._mainloop)

        try:
            self.proxy = self.bus.get_object(BUS_NAME, BUS_PATH)
        except dbus.exceptions.DBusException as e:
            raise errors.UnavailableSource(_("Can't connect to DBus system bus '{0}' path '{1}': {2}").format(BUS_NAME, BUS_PATH, e.message))

        try:
            self.interface = dbus.Interface(self.proxy, BUS_IFACE)
        except dbus.exceptions.DBusException as e:
            raise errors.UnavailableSource(_("Can't get interface '{0}' on path '{1}' in bus '{2}': {3}").format(BUS_IFACE, BUS_PATH, BUS_NAME, e.message))

    def _close_problems_bus(self):
        self.proxy = None
        self.interface = None
        self.bus.close()
        self.bus = None

    def _send_dbus_message(self, method, *args):
            try:
                return method(self.interface, *args)
            except dbus.exceptions.DBusException as e:
                if e.get_dbus_name() == "org.freedesktop.DBus.Error.ServiceUnknown":
                    logging.warning("Reconnecting to dbus: {0}".format(e.message))
                    self._close_problems_bus()
                    self._connect_to_problems_bus()
                    return method(self.interface, *args)

                raise

    def _on_new_problem(self, *args):
        if len(args) < 2:
            logging.debug("Received new problem signal with invalid number of arguments {0}".format(args))
            return

        if len(args) > 2 and int(args[2]) != os.getuid():
            logging.debug("Received new problem signal with different uid '{0}' ('{1}')".format(args[2], os.getuid()))
            return

        self.process_new_problem_id(str(args[1]))

    def get_items(self, problem_id, *args):
        info = {}

        if len(args) != 0:
            try:
                info = self._send_dbus_message(lambda iface, *params: iface.GetInfo(*params), problem_id, args)
            except dbus.exceptions.DBusException as e:
                if e.get_dbus_name() in ["org.freedesktop.problems.AuthFailure", "org.freedesktop.problems.InvalidProblemDir"]:
                    raise errors.InvalidProblem(e.message)

                logging.warning(_("Can't get problem data from DBus service: {0!s}").format(e.message))

        return info

    def impl_get_problems(self):
        conf = config.get_configuration()

        prblms = None

        try:
            if conf['all_problems']:
                prblms = self._send_dbus_message(lambda iface, *args: iface.GetAllProblems(*args))
            else:
                prblms  = self._send_dbus_message(lambda iface, *args: self.interface.GetProblems(*args))
        except dbus.exceptions.DBusException as e:
            logging.warning(_("Can't get list of problems from DBus service: {0!s}").format(e.message))
            return None

        return (str(pid) for pid in prblms)

    def impl_delete_problem(self, problem_id):
        try:
            self._send_dbus_message(lambda iface, *args: iface.DeleteProblem(*args), [problem_id])
            return True
        except dbus.exceptions.DBusException as e:
            if e.get_dbus_name() in ["org.freedesktop.problems.AuthFailure", "org.freedesktop.problems.InvalidProblemDir"]:
                raise errors.InvalidProblem(e.message)

            logging.warning(_("Can't delete problem over DBus service: {0!s}").format(e.message))
            return False
