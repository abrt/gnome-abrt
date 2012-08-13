import datetime

import application

class ProblemSource(object):

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
        except ValueError:
            pass

    def notify(self):
        for observer in self._observers:
            observer.problem_source_updated(self)

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

        return None

    def delete(self):
        self.source.delete(self.problem_id)

    def is_reported(self):
        return None != self['reported']

    def get_application(self):
        if not self.app:
            self.app = application.find_application(self['component'],
                                                    self['executable'])

        return self.app

class MultipleSources(ProblemSource):

    def __init__(self, *args):
        super(MultipleSources, self).__init__()
        self.sources = args

        class SourceObserver:
            def __init__(self, parent):
                self.parent = parent

            def problem_source_updated(self, source):
                slef.parent.notify()

        observer = SourceObserver(self)
        for s in self.sources:
            s.attach(observer)

    def get_items(self, problem_id, *args):
        return problem_id.source.get_items(problem_id, *args)

    def get_problems(self):
        result = []
        for s in self.sources:
            result.extend(s.get_problems())

        return result

    def delete_problem(self, problem_id):
        return problem_id.source.delete_problem(problem_id)


