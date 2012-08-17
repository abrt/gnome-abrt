import os
import sys
import logging

# pygobject
from gi.repository import GLib

# pyinotify
import pyinotify
from pyinotify import WatchManager, Notifier, ProcessEvent

# libreport-python
import report

# gnome-abrt
import problems
import errors
from l10n import _

class INOTIFYGlibSource(GLib.Source):

    def __init__(self, wm, path, mask, handler):
        super(INOTIFYGlibSource, self).__init__()

        self.wm = wm
        # set timeout to 0 -> don't wait
        self.notifier = Notifier(self.wm, handler, timeout=0)
        self.wdd = self.wm.add_watch(path, mask, rec=True)

    def prepare(self, *args):
        # return 0 -> don't wait
        return (self.notifier.check_events(), 0)

    def check(self, *args):
        # just to be sure
        return self.notifier.check_events()

    def dispatch(self, *args):
        self.notifier.read_events()
        self.notifier.process_events()
        return True

    def finalize(self, *args):
        self.notifier.stop()

class INOTIFYHandler(ProcessEvent):

    def __init__(self, source):
        super(INOTIFYHandler, self).__init__()

        self.source = source

    def process_IN_MOVED_TO(self, event):
        try:
            # !!! FIXIT, TODO - ugly hack, insert to cache doesn't require constructed object !!!!
            # even more it uses private method of source !!!
            # !!! CachedSource have to have an factory method !!!
            self.source.insert_to_cache(problems.Problem(os.path.join(event.path, event.name), self.source))
        except errors.InvalidProblem as e:
            logging.warning(e.message)
        except errors.UnavailableSource as e:
            logging.warning(e.message)

class DirectoryProblemSource(problems.CachedSource):

    def __init__(self, directory, context=None):
        super(DirectoryProblemSource, self).__init__()

        self.directory = directory

        # context is the instance variable because the source is to be used in Problems
        self._context = context
        if self._context:
            self._wm = WatchManager()
            self._gsource = INOTIFYGlibSource(self._wm, self.directory,
                                              pyinotify.IN_MOVED_TO, INOTIFYHandler(self))
            self._gsource.attach(self._context)

    def get_items(self, problem_id, *args):
        if len(args) == 0:
            return {}

        dd = report.dd_opendir(problem_id)
        if not dd:
            raise errors.InvalidProblem(_("Can't open directory"))

        items = {}
        for field_name in args:
            value = dd.load_text(field_name, 15)
            if value:
                items[field_name] = value

        dd.close()

        return items

    def impl_get_problems(self):
        all_problems = []

        for dir_entry in os.listdir(self.directory):
            problem_id = os.path.join(self.directory, dir_entry)
            if os.path.isdir(problem_id):
                dd = report.dd_opendir(problem_id)
                if dd:
                    dd.close()
                    try:
                        all_problems.append(problems.Problem(problem_id, self))
                    except errors.InvalidProblem as e:
                        loggin.warning(_("Invalid problem directory '{0}': {1}").format(problem_id, e.message))

        return all_problems

    def impl_delete_problem(self, problem_id):
        dd = report.dd_opendir(problem_id)
        if not dd:
            return False

        # TODO : delete over abrtd
        dd.delete()
        # dd.close()
        return True
