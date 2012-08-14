import os

from gi.repository import Gtk
from gi.repository import Gdk

import problems
from tools import fancydate
from l10n import _, GETTEXT_PROGNAME

class OopsWindow(Gtk.ApplicationWindow):

    def __init__(self, application, source, controller):
        super(OopsWindow, self).__init__(title=_('Oops!'), application=application)

        self.set_default_size(640, 480)

        if os.path.exists('oops.glade'):
            self._load_widgets_from_builder(filename='oops.glade')
        else:
            import gnome_abrt_glade
            self._load_widgets_from_builder(content=gnome_abrt_glade.GNOME_ABRT_GLADE_CONTENTS)

        self._source = source
        self._controller = controller
        self._reload_problems(self._source)
        self.selected_problem = None

        class SourceObserver:
            def __init__(self, wnd):
                self.wnd = wnd

            def problem_source_updated(self, source):
                self.wnd._reload_problems(source)

        self._source.attach(SourceObserver(self))

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

        builder.connect_signals(self)

    def _reload_problems(self, source):
        self.ls_problems.clear()
        problems = source.get_problems()
        for p in problems:
            app = p.get_application()
            # not localizable, it is a format for tree view column
            self.ls_problems.append(["{0!s}\n{1!s}".format(app.name, p['type']),
                                     "{0!s}\n{1!s}".format(fancydate(p['date']), p['count']),
                                     p])

        if len(problems) > 0:
            self.tv_problems.set_cursor(0)
            self._set_problem(problems[0])
        else:
            self._set_problem(None)

    def _set_problem(self, problem):
        if problem:
            self.nb_problem_layout.set_current_page(0)
            self.selected_problem = problem
            app = problem['application']
            self.lbl_reason.set_text(app.name + _(' crashed'));
            self.lbl_summary.set_text(problem['reason'])
            self.lbl_app_name_value.set_text(app.name)
            self.lbl_app_version_value.set_text(problem['package'])

            if app.icon:
                self.img_app_icon.set_from_pixbuf(app.icon)
            else:
                self.img_app_icon.set_from_stock(Gtk.STOCK_MISSING_IMAGE, 3)

            if problem['is_reported']:
                self.lbl_reported_value.set_text(_('yes'))
            else:
                self.lbl_reported_value.set_text(_('no'))

            self.tb_delete.set_sensitive(True)
            self.tb_report.set_sensitive(True)
            self.btn_detail.set_sensitive(True)
        else:
            self.nb_problem_layout.set_current_page(1)
            self.tb_delete.set_sensitive(False)
            self.tb_report.set_sensitive(False)
            self.btn_detail.set_sensitive(False)

    def _get_selected(self, selection):
        model, path = selection.get_selected()
        if path:
            return model[path][2]

        return None

    def on_tvs_problems_changed(self, selection):
        self._set_problem(self._get_selected(selection))

    def on_gac_delete_activate(self, action):
        self._controller.delete(self._get_selected(self.tvs_problems))

    def on_gac_detail_activate(self, action):
        self._controller.detail(self._get_selected(self.tvs_problems))

    def on_gac_report_activate(self, action):
        self._controller.report(self._get_selected(self.tvs_problems))

    def on_te_search_focus_out_event(self, search_entry, data):
        search_entry.set_text("")

    def on_te_search_changed(self, search_entry):
        def match_pattern(pattern, problem):
            def item_match(pattern, problem, items):
                for i in items:
                    v = problem[i]
                    if v and pattern in v:
                        return True

            return item_match(pattern, problem, ['component', 'reason', 'executable', 'package']) or pattern in problem['application'].name

        pattern = search_entry.get_text()

        if len(pattern) == 0:
            return

        model, it = self.tvs_problems.get_selected()

        if not it:
            return

        origin_path = model.get_path(it)
        while True:
             problem = self.ls_problems[it][2]

             if match_pattern(pattern, problem):
                 self.tvs_problems.select_iter(it)
                 self.tv_problems.scroll_to_cell(model.get_path(it))
                 break

             it = model.iter_next(it)

             if not it:
                 it = model.get_iter_first()

             if model.get_path(it) == origin_path:
                break
