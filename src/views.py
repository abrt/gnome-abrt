from gi.repository import Gtk
from gi.repository import Gdk

import problems
from tools import fancydate

class OopsWindow(Gtk.ApplicationWindow):

    def __init__(self, application, source, controller):
        super(OopsWindow, self).__init__(title='Oops!', application=application)

        self.set_default_size(640, 480)

        self._load_widgets_from_file('oops.glade')
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

    def _load_widgets_from_file(self, file_name):
        builder = Gtk.Builder()
        builder.add_from_file(file_name)
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
        self.tvs_problems = builder.get_object('tvs_problems')
        self.img_app_icon = builder.get_object('img_app_icon')

        builder.connect_signals(self)

    def _reload_problems(self, source):
        for p in source.get_problems():
            app = p.get_application()
            self.ls_problems.append(["%s\n%s" % (app.name, p['type']),
                                     "%s\n%s" % (fancydate(p['date']), p['count']),
                                     p])

    def _set_problem(self, problem):
        self.selected_problem = problem
        app = problem['application']
        self.lbl_reason.set_text(app.name + ' crashed');
        self.lbl_summary.set_text(problem['reason'])
        self.lbl_app_name_value.set_text(app.name)
        self.lbl_app_version_value.set_text(problem['package'])
        self.img_app_icon.set_from_pixbuf(app.icon)

        if problem['is_reported']:
            self.lbl_reported_value.set_text('yes')
        else:
            self.lbl_reported_value.set_text('no')

    def _get_selected(self, selection):
        model, path = selection.get_selected()
        return model[path][2]

    def on_tvs_problems_changed(self, selection):
        self._set_problem(self._get_selected(selection))

    def on_gac_delete_activate(self, action):
        self._controller.delete(self._get_selected(self.tvs_problems))

    def on_gac_detail_activate(self, action):
        self._controller.detail(self._get_selected(self.tvs_problems))

    def on_gac_report_activate(self, action):
        self._controller.report(self._get_selected(self.tvs_problems))
