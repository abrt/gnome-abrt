import os
import signal

class Controller(object):

    def __init__(self, source):
        signal.signal(signal.SIGCHLD, lambda signum, frame: self._handle_signal(signum))
        self.source = source

    def _handle_signal(self, signum):
        self.source.drop_cache()
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

