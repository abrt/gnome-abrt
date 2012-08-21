import datetime
import logging

# gnome-abrt
import application
import errors
import problems
from l10n import _

class ProblemSource(object):
    NEW_PROBLEM = 0
    DELETED_PROBLEM = 1
    UPDATED_PROBLEM = 2

    def __init__(self):
        self._observers = set()

    def get_items(self, problem_id, *args):
        pass

    def get_problems(self):
        pass

    def delete_problem(self, problem_id):
        pass

    def attach(self, observer):
        if not observer in self._observers:
            self._observers.add(observer)

    def detach(self, observer):
        try:
            self._observers.remove(observer)
        except ValueError as e:
            logging.debug(e.message)

    def notify(self, update_type=None, problem=None):
        logging.debug("Notify")
        for observer in self._observers:
            observer.problem_source_updated(self, update_type, problem)

    def drop_cache(self):
        pass

class Problem:

    def __init__(self, problem_id, source):
        self.problem_id = problem_id
        self.source = source
        self.app = None
        self.data = source.get_items(problem_id,
                                     'component',
                                     'executable',
                                     'time',
                                     'reason')

    def __str__(self):
        return self.problem_id

    def __eq__(self, other):
        if isinstance(other, str):
            return self.problem_id == other
        elif isinstance(other, Problem):
            return self.problem_id == other.problem_id

        raise TypeError('Not allowed type in __eq__')

    def __loaditems__(self, *args):
        items = self.source.get_items(self.problem_id, *args)
        for k, v in items.items():
            self.data[k] = v

        return items

    def __getitem__(self, item, cached=True):
        if item == 'date':
            return datetime.datetime.fromtimestamp(float(self['time']))
        elif item == 'application':
            return self.get_application()
        elif item == 'is_reported':
            return self.is_reported()

        if cached and item in self.data:
            return self.data[item]

        loaded = self.__loaditems__(item)
        if item in loaded:
            return loaded[item]

        if item == 'count':
            return 1

        return None

    def delete(self):
        self.source.delete_problem(self.problem_id)

    def is_reported(self):
        return not self['reported_to'] is None

    def get_application(self):
        if not self.app:
            self.app = application.find_application(self['component'],
                                                    self['executable'])

        return self.app

class MultipleSources(ProblemSource):

    def __init__(self, *args):
        super(MultipleSources, self).__init__()

        if len(args) == 0:
            raise ValueError("At least one source must be passed")

        self.sources = args

        class SourceObserver:
            def __init__(self, parent):
                self.parent = parent

            def problem_source_updated(self, source, update_type=None, problem=None):
                self.parent.notify(update_type, problem)

        observer = SourceObserver(self)
        for s in self.sources:
            s.attach(observer)

        self._disable_notify = False

    def get_items(self, problem_id, *args):
        pass

    def get_problems(self):
        result = []
        for s in self.sources:
            result.extend(s.get_problems())

        return result

    def delete_problem(self, problem_id):
        pass

    def notify(self, update_type=None, problem=None):
        if self._disable_notify:
            return

        super(MultipleSources, self).notify(update_type, problem)

    def drop_cache(self):
        self._disable_notify = True

        try:
            for s in self.sources:
                s.drop_cache()
        finally:
            self._disable_notify = False

        self.notify()

class CachedSource(ProblemSource):

    def __init__(self):
        super(CachedSource, self).__init__()

        self._cache = None

    def get_problems(self):
        if not self._cache:
            self._cache = []
            for prblmid in self.impl_get_problems():
                try:
                    self._cache.append(self.create_new_problem(prblmid))
                except errors.InvalidProblem as e:
                    logging.warning(e.message)
                except errors.UnavailableSource as e:
                    logging.warning(e.message)

        return self._cache if self._cache else []

    def drop_cache(self):
        self._cache = None
        self.notify()

    def _insert_to_cache(self, problem):
        if self._cache:
            if problem in self._cache:
                raise errors.InvalidProblem(_("Problem '{0}' is already in the cache").format(problem.problem_id))

            self._cache.append(problem)

    def delete_problem(self, problem_id):
        if not self.impl_delete_problem(problem_id):
            return

        try:
            p = self._cache[self._cache.index(problem_id)]
            self._cache.remove(problem_id)
            self.notify(ProblemSource.DELETED_PROBLEM, p)
            return
        except ValueError as e:
            logging.warning(_('Not found in cache but deleted: {0}'), e.message)
            self._cache = None

        self.notify()

    def create_new_problem(self, problem_id):
        return problems.Problem(problem_id, self)

    def process_new_problem_id(self, problem_id):
        try:
            p = self.create_new_problem(problem_id)
            self._insert_to_cache(p)
            self.notify(ProblemSource.NEW_PROBLEM, p)
        except errors.InvalidProblem as e:
            logging.warning(_("Can't process '{0}': {1}").format(problem_id, e.message))
        except errors.UnavailableSource as e:
            logging.warning(_("Source failed on processing of '{0}': {1}").format(problem_id, e.message))
