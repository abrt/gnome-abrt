import os

class Controller(object):

    def __init__(self):
        pass

    def report(self, problem):
        self._run_event_on_problem("report-gui", problem)

    def delete(self, problem):
        problem.delete()

    def detail(self, problem):
        self._run_event_on_problem("open-gui", problem)

    def _run_event_on_problem(self, event, problem):
        try:
            if os.fork() == 0:
                os.execvp("/usr/libexec/abrt-handle-event", ["/usr/libexec/abrt-handle-event", "-e", event, "--", problem.problem_id])
        except OSError, e:
            print e

