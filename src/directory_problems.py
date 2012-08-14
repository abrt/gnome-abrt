import os
import report
import problems
import errors
from l10n import _

class DirectoryProblemSource(problems.ProblemSource):

    def __init__(self, directory):
        super(DirectoryProblemSource, self).__init__()

        self.directory = directory

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

    def get_problems(self):
        problem_ids = []

        for dir_entry in os.listdir(self.directory):
            problem_id = os.path.join(self.directory, dir_entry)
            if os.path.isdir(problem_id):
                dd = report.dd_opendir(problem_id)
                if dd:
                    dd.close()
                    try:
                        problem_ids.append(problems.Problem(problem_id, self))
                    except errors.InvalidProblem as e:
                        loggin.warning(_("Invalid problem directory '{0}': {1}").format(problem_id, e.message))

        return problem_ids

    def delete_problem(self, problem_id):
        dd = report.dd_opendir(problem_id)
        if dd:
            # TODO : delete over abrtd
            dd.delete()
            # dd.close()
            self.notify()
