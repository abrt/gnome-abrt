import dbus
import problems
import config

class DBusProblemSource(problems.ProblemSource):

    def __init__(self):
        super(DBusProblemSource, self).__init__()

        bus = dbus.SystemBus()
        self.proxy = bus.get_object('org.freedesktop.problems',
                                    '/org/freedesktop/problems')
        self.interface = dbus.Interface(self.proxy,
                                        'org.freedesktop.problems')

        class ConfigObserver():
            def __init__(self, source):
                self.source = source

            def option_updated(self, conf, option):
                if option == "all_problems":
                    self.source.notify()

        conf = config.get_configuration()
        conf.set_watch("all_problems", ConfigObserver(self))

    def get_items(self, problem_id, *args):
        if len(args) == 0:
            return {}

        return self.interface.GetInfo(problem_id, args)

    def get_problems(self):
        prblms = None
        conf = config.get_configuration()
        if conf['all_problems']:
            prblms = self.interface.GetAllProblems()
        else:
            prblms = self.interface.GetProblems()

        return [problems.Problem(pid, self) for pid in prblms]

    def delete_problem(self, problem_id):
        self.interface.DeleteProblem([problem_id])
        self.notify()
