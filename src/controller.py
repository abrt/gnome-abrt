import os
import signal

class Controller(object):

    def __init__(self, source):
        self.source = source
        self.run_event_fn = self._first_event_run

    def _handle_signal(self, signum):
        self.source.drop_cache()

    def report(self, problem):
        self.run_event_fn("report-gui", problem)

    def delete(self, problem):
        problem.delete()

    def detail(self, problem):
        self.run_event_fn("open-gui", problem)

    def _first_event_run(self, event, problem):
        signal.signal(signal.SIGCHLD, lambda signum, frame: self._handle_signal(signum))

        self.run_event_fn = self._run_event_on_problem
        self.run_event_fn(event, problem)

    def _run_event_on_problem(self, event, problem):
        try:
            if os.fork() == 0:
                os.execvp("/usr/libexec/abrt-handle-event", ["/usr/libexec/abrt-handle-event", "-e", event, "--", problem.problem_id])
        except OSError, e:
            print e

