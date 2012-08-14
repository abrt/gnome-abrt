import dbus
import logging

import problems
import config
import errors

BUS_NAME = 'org.freedesktop.problems'
BUS_PATH = '/org/freedesktop/problems'
BUS_IFACE = 'org.freedesktop.problems'

class DBusProblemSource(problems.ProblemSource):

    def __init__(self):
        super(DBusProblemSource, self).__init__()

        # I can't find any description of raised exceptions
        bus = dbus.SystemBus()

        try:
            self.proxy = bus.get_object(BUS_NAME, BUS_PATH)
        except dbus.exceptions.DBusException as e:
            raise errors.UnavailableSource("Can't connect to DBus system bus '{0}' path '{1}': {2}".format(BUS_NAME, BUS_PATH, e.message))

        try:
            self.interface = dbus.Interface(self.proxy, BUS_IFACE)
        except dbus.exceptions.DBusException as e:
            raise errors.UnavailableSource("Can't get interface '{0}' on path '{1}' in bus '{2}': {3}".format(BUS_IFACE, BUS_PATH, BUS_NAME, e.message))

        class ConfigObserver():
            def __init__(self, source):
                self.source = source

            def option_updated(self, conf, option):
                if option == "all_problems":
                    self.source.notify()

        conf = config.get_configuration()
        conf.set_watch("all_problems", ConfigObserver(self))

    def get_items(self, problem_id, *args):
        info = {}

        if len(args) != 0:
            try:
                info = self.interface.GetInfo(problem_id, args)
            except dbus.exceptions.DBusException as e:
                logging.warning("Can't get problem data from DBus service: {0!s}".format(e.message))

        return info

    def get_problems(self):
        conf = config.get_configuration()

        prblms = None

        try:
            if conf['all_problems']:
                prblms = self.interface.GetAllProblems()
            else:
                prblms  = self.interface.GetProblems()
        except dbus.exceptions.DBusException as e:
            logging.warning("Can't get list of problems from DBus service: {0!s}".format(e.message))
            return []

        return [problems.Problem(pid, self) for pid in prblms]

    def delete_problem(self, problem_id):
        try:
            self.interface.DeleteProblem([problem_id])
        except dbus.exceptions.DBusException as e:
            logging.warning("Can't delete problem over DBus service: {0!s}".format(e.message))
            return

        self.notify()
