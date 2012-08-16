import os
import signal

class Controller(object):

    def __init__(self):
        signal.signal(signal.SIGCHLD, lambda signum, frame: self._handle_signal(signum))
        self.view = None

    def _handle_signal(self, signum):
        if self.view:
            self.view.refresh()

    def set_view(self, view):
        self.view = view

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

