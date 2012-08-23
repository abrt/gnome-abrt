import os
import time

from gi.repository import Gtk
from gi.repository import Gdk

import problems
import config
from tools import fancydate
from l10n import _, GETTEXT_PROGNAME

def problems_filter(model, it, data):
    def match_pattern(pattern, problem):
        def item_match(pattern, problem):
            for i in ['component', 'reason', 'executable', 'package']:
                v = problem[i]
                if v and pattern in v:
                    return True

        return (item_match(pattern, problem)
                or pattern in problem['application'].name
                or pattern in problem.problem_id)

    pattern = data.current_pattern

    if len(pattern) == 0:
        return True

    return match_pattern(pattern, model[it][2])


class ProblemsFilter:

    def __init__(self, window, view):
        self.current_pattern = ""
        self.window = window
        self.view = view
        self.tm_filter = view.get_model().filter_new()
        self.tm_filter.set_visible_func(problems_filter, self)
        self.view.set_model(self.tm_filter)

    def set_pattern(self, pattern):
        self.current_pattern = pattern
        self.tm_filter.refilter()

        it = self.view.get_model().get_iter_first()
        if it:
            self.window._select_problem_iter(it)

# default on None :)
def doN(text, default_text):
    if text:
        return text
    return default_text


def problem_to_storage_values(problem):
    # not localizable, it is a format for tree view column
    app = problem.get_application()
    return ["{0!s}\n{1!s}".format(doN(app.name, _("N/A")), doN(problem['type'], "")),
            "{0!s}\n{1!s}".format(fancydate(problem['date']), problem['count']),
            problem]

def time_sort_func(model, first, second, data):
    return time.mktime(model[first][2]['date'].timetuple()) - time.mktime(model[second][2]['date'].timetuple())

class OopsWindow(Gtk.ApplicationWindow):

    def __init__(self, application, source, controller):
        super(OopsWindow, self).__init__(title=_('Oops!'), application=application)

        self.set_default_size(640, 480)

        if os.path.exists('oops.glade'):
            self._load_widgets_from_builder(filename='oops.glade')
        else:
            import gnome_abrt_glade
            self._load_widgets_from_builder(content=gnome_abrt_glade.GNOME_ABRT_GLADE_CONTENTS)

        self.selected_problem = None
        self._source = source
        self._reloading = False
        self._controller = controller

        self.ls_problems.set_sort_column_id(0,Gtk.SortType.DESCENDING)
        self.ls_problems.set_sort_func(0, time_sort_func, None)
        self._filter = ProblemsFilter(self, self.tv_problems)


        class SourceObserver:
            def __init__(self, wnd):
                self.wnd = wnd

            def changed(self, source, change_type=None, problem=None):
                if not change_type:
                    self.wnd._reload_problems(source)
                elif change_type == problems.ProblemSource.NEW_PROBLEM:
                    self.wnd._add_problem_to_storage(problem)
                elif change_type == problems.ProblemSource.DELETED_PROBLEM:
                    self.wnd._remove_problem_from_storage(problem)
                elif change_type == problems.ProblemSource.CHANGED_PROBLEM:
                    self.wnd._update_problem_in_storage(problem)

        self._source.attach(SourceObserver(self))

        self.tv_problems.grab_focus()
        self._reload_problems(self._source)

    def _load_widgets_from_builder(self, filename=None, content=None):
        builder = Gtk.Builder()
        builder.set_translation_domain(GETTEXT_PROGNAME)

        if filename:
            builder.add_from_file(filename)
        elif content:
            builder.add_from_string(content)
        else:
            raise ValueError("One of the arguments must be set")

        self.gr_main_layout = builder.get_object('gr_main_layout')
        wnd = builder.get_object('wnd_main')
        wnd.remove(self.gr_main_layout)
        self.add(self.gr_main_layout)

        self.ls_problems = builder.get_object('ls_problems')
        self.lbl_reason = builder.get_object('lbl_reason')
        self.lbl_summary = builder.get_object('lbl_summary')
        self.lbl_app_name_value = builder.get_object('lbl_app_name_value')
        self.lbl_app_version_value = builder.get_object('lbl_app_version_value')
        self.lbl_reported_value = builder.get_object('lbl_reported_value')
        self.tv_problems = builder.get_object('tv_problems')
        self.tvs_problems = builder.get_object('tvs_problems')
        self.img_app_icon = builder.get_object('img_app_icon')
        self.nb_problem_layout = builder.get_object('nb_problem_layout')
        self.tb_delete = builder.get_object('tb_delete')
        self.tb_report = builder.get_object('tb_report')
        self.btn_detail = builder.get_object('btn_detail')
        self.te_search = builder.get_object('te_search')
        self.chb_all_problems = builder.get_object('chb_all_problems')

        builder.connect_signals(self)

    def _find_problem_iter(self, problem):
        pit = self.ls_problems.get_iter_first()
        while pit:
            if self.ls_problems[pit][2] == problem:
                return pit
            pit = self.ls_problems.iter_next(pit)

    def _add_problem_to_storage(self, problem):
        self.ls_problems.append(problem_to_storage_values(problem))

    def _remove_problem_from_storage(self, problem):
        pit = self._find_problem_iter(problem)
        if pit:
            self.ls_problems.remove(pit)

    def _update_problem_in_storage(self, problem):
        pit = self._find_problem_iter(problem)
        if pit:
            values = problem_to_storage_values(problem)
            for i in xrange(0, len(values)-1):
                self.ls_problems.set_value(pit, i, values[i])

        if problem == self._get_selected(self.tvs_problems):
            self._set_problem(problem)

    def _reload_problems(self, source):
        self._reloading = True
        try:
            self.ls_problems.clear()
            problems = source.get_problems()
            for p in problems:
                self._add_problem_to_storage(p)
        finally:
            self._reloading = False

        if len(problems) > 0:
            self._select_problem_iter(self.tv_problems.get_model().get_iter_first())
            self._set_problem(problems[0])
        else:
            self._set_problem(None)

    def _select_problem_iter(self, pit):
         self.tvs_problems.select_iter(pit)
         self.tv_problems.scroll_to_cell(self.tv_problems.get_model().get_path(pit))

    def _set_problem(self, problem):
        self.selected_problem = problem

        sensitive_btn = not problem is None
        self.tb_delete.set_sensitive(sensitive_btn)
        self.tb_report.set_sensitive(sensitive_btn)
        self.btn_detail.set_sensitive(sensitive_btn)

        if problem:
            self.nb_problem_layout.set_current_page(0)
            app = problem['application']
            self.lbl_reason.set_text(doN(app.name, _("N/A")) + _(' crashed'));
            self.lbl_summary.set_text(doN(problem['reason'], ""))
            self.lbl_app_name_value.set_text(doN(app.name, _("N/A")))
            self.lbl_app_version_value.set_text(doN(problem['package'], ""))

            if app.icon:
                self.img_app_icon.set_from_pixbuf(app.icon)
            else:
                self.img_app_icon.set_from_stock(Gtk.STOCK_MISSING_IMAGE, 3)

            if problem['is_reported']:
                self.lbl_reported_value.set_text(_('yes'))
            else:
                self.lbl_reported_value.set_text(_('no'))
        else:
            self.nb_problem_layout.set_current_page(1)

    def _get_selected(self, selection):
        model, path = selection.get_selected()
        if path:
            return model[path][2]

        return None

    def on_tvs_problems_changed(self, selection):
        if not self._reloading:
            self._set_problem(self._get_selected(selection))

    def on_gac_delete_activate(self, action):
        self._controller.delete(self._get_selected(self.tvs_problems))

    def on_gac_detail_activate(self, action):
        self._controller.detail(self._get_selected(self.tvs_problems))

    def on_gac_report_activate(self, action):
        self._controller.report(self._get_selected(self.tvs_problems))

    def on_te_search_changed(self, entry):
        self._filter.set_pattern(entry.get_text())

    def on_gac_opt_all_problems_activate(self, action):
        conf = config.get_configuration()
        conf['all_problems'] = self.chb_all_problems.get_active()
