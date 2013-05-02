# coding=UTF-8

## Copyright (C) 2012 ABRT team <abrt-devel-list@redhat.com>
## Copyright (C) 2001-2005 Red Hat, Inc.

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA  02110-1335  USA

import os
import time
import logging
import subprocess
import locale

#pygobject
#pylint: disable=E0611
from gi.repository import Gtk
#pylint: disable=E0611
from gi.repository import Gdk

import gnome_abrt.problems as problems
import gnome_abrt.config as config
import gnome_abrt.wrappers as wrappers
import gnome_abrt.errors as errors
from gnome_abrt.tools import fancydate
from gnome_abrt.l10n import _, GETTEXT_PROGNAME


def problems_filter(model, itrtr, data):
    def match_pattern(pattern, problem):
        def item_match(pattern, problem):
            for i in ['component', 'reason',
                        'executable', 'package']:
                val = problem[i]
                if val and pattern in val:
                    return True

        return (item_match(pattern, problem)
                or pattern in problem['application'].name
                or pattern in problem.problem_id)

    pattern = data.current_pattern

    if len(pattern) == 0:
        return True

    return match_pattern(pattern, model[itrtr][2])


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

        itrtr = self.view.get_model().get_iter_first()
        if itrtr:
            self.window._select_problem_iter(itrtr)


def problem_to_storage_values(problem):
    # not localizable, it is a format for tree view column
    app = problem.get_application()
    return ["{0!s}\n{1!s}".format(app.name or _("N/A"),
                                  problem['type'] or ""),
            "{0!s}\n{1!s}".format(fancydate(problem['date_last']),
                                  problem['count']),
            problem]

#pylint: disable=W0613
def time_sort_func(model, first, second, view):
    try:
        lhs = model[first][2]['date_last'].timetuple()
        rhs = model[second][2]['date_last'].timetuple()
        return time.mktime(lhs) - time.mktime(rhs)
    except errors.InvalidProblem as ex:
        view._remove_problem_from_storage(ex.problem_id)
        logging.debug(ex.message)
        return 0

#pylint: disable=R0902
class OopsWindow(Gtk.ApplicationWindow):
    class OopsGtkBuilder(object):
        def __init__(self):
            builder = Gtk.Builder()
            self._builder = builder
            builder.set_translation_domain(GETTEXT_PROGNAME)

            if os.path.exists('oops.glade'):
                builder.add_from_file(filename='oops.glade')
            else:
                from gnome_abrt import gnome_abrt_glade
                builder.add_from_string(
                            gnome_abrt_glade.GNOME_ABRT_GLADE_CONTENTS)

            self.wnd_main = builder.get_object('wnd_main')
            self.gr_main_layout = builder.get_object('gr_main_layout')
            self.ls_problems = builder.get_object('ls_problems')
            self.lbl_reason = builder.get_object('lbl_reason')
            self.lbl_summary = builder.get_object('lbl_summary')
            self.lbl_app_name_value = builder.get_object('lbl_app_name_value')
            self.lbl_app_version_value = builder.get_object(
                    'lbl_app_version_value')
            self.lbl_detected_value = builder.get_object('lbl_detected_value')
            self.lbl_reported_value = builder.get_object('lbl_reported_value')
            self.tv_problems = builder.get_object('tv_problems')
            self.tvs_problems = builder.get_object('tvs_problems')
            self.img_app_icon = builder.get_object('img_app_icon')
            self.nb_problem_layout = builder.get_object('nb_problem_layout')
            self.btn_delete = builder.get_object('btn_delete')
            self.btn_report = builder.get_object('btn_report')
            self.btn_detail = builder.get_object('btn_detail')
            self.te_search = builder.get_object('te_search')
            self.chb_all_problems = builder.get_object('chb_all_problems')
            self.vbx_links = builder.get_object('vbx_links')
            self.vbx_problem_messages = builder.get_object(
                    'vbx_problem_messages')
            self.gac_report = builder.get_object('gac_report')
            self.gac_delete = builder.get_object('gac_delete')
            self.gac_open_directory = builder.get_object('gac_open_directory')
            self.gac_copy_id = builder.get_object('gac_copy_id')
            self.menu_problem_item = builder.get_object('menu_problem_item')
            self.ag_accelerators = builder.get_object('ag_accelerators')

        def connect_signals(self, implementor):
            self._builder.connect_signals(implementor)

        def __getattr__(self, name):
            obj = self._builder.get_object(name)

            if obj is None:
                raise AttributeError("Builder has not member '{0}'"
                        .format(name))

            return obj


    def __init__(self, application, source, controller):
        Gtk.ApplicationWindow.__init__(self,
                            title=_('Automatic Bug Reporting Tool'),
                            application=application)

        self._builder = OopsWindow.OopsGtkBuilder()
        self.set_default_size(*self._builder.wnd_main.get_size())
        self._builder.wnd_main.remove(self._builder.gr_main_layout)
        #pylint: disable=E1101
        self.add(self._builder.gr_main_layout)

        # move accelators group from the design window to this window
        self.add_accel_group(self._builder.ag_accelerators)

        css_prv = Gtk.CssProvider()
        css_prv.load_from_data("GtkViewport {\n"
                               "  background-color : @theme_bg_color;\n"
                               "}\n")
        stl_ctx = self.get_style_context()
        stl_ctx.add_provider_for_screen(stl_ctx.get_screen(), css_prv, 6000)
        self._builder.connect_signals(self)

        self.selected_problem = None
        self._source = source
        self._reloading = False
        self._controller = controller

        self._builder.ls_problems.set_sort_column_id(0, Gtk.SortType.DESCENDING)
        self._builder.ls_problems.set_sort_func(0, time_sort_func, self)
        self._filter = ProblemsFilter(self, self._builder.tv_problems)

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


        self._source_observer = SourceObserver(self)
        self._source.attach(self._source_observer)

        self._builder.tv_problems.grab_focus()
        self._reload_problems(self._source)

        class OptionsObserver:
            def __init__(self, wnd):
                self.wnd = wnd

            def option_updated(self, conf, option):
                if option == 'problemid' and conf[option]:
                    self.wnd._select_problem_by_id(conf[option])

        self._options_observer = OptionsObserver(self)
        conf = config.get_configuration()
        conf.set_watch('problemid', self._options_observer)
        self._options_observer.option_updated(conf, 'problemid')
        self._builder.btn_detail.set_visible(conf['expert'])
        self._builder.mi_detail.set_visible(conf['expert'])

    def _find_problem_iter(self, problem, model):
        pit = model.get_iter_first()
        while pit:
            try:
                if model[pit][2] == problem:
                    return pit
            except errors.InvalidProblem as ex:
                self._remove_problem_from_storage(ex.problem_id)
                logging.debug(ex.message)

            pit = model.iter_next(pit)

        return None

    def _add_problem_to_storage(self, problem):
        """Adds a problem to the storage

        Returns True if the problem was successfully added to the storage;
        otherwise returns False
        """
        try:
            self._builder.ls_problems.append(problem_to_storage_values(problem))
            return True
        except errors.InvalidProblem as ex:
            self._remove_problem_from_storage(ex.problem_id)
            logging.debug(ex.message)
            return False

    def _remove_problem_from_storage(self, problem):
        if problem is None:
            return

        pit = self._find_problem_iter(problem, self._builder.ls_problems)
        if pit:
            self._builder.ls_problems.remove(pit)

    def _update_problem_in_storage(self, problem):
        pit = self._find_problem_iter(problem, self._builder.ls_problems)
        if pit:
            try:
                values = problem_to_storage_values(problem)
                for i in xrange(0, len(values)-1):
                    self._builder.ls_problems.set_value(pit, i, values[i])
            except errors.InvalidProblem as ex:
                self._remove_problem_from_storage(ex.problem_id)
                logging.debug(ex.message)
                return

        try:
            if problem in self._get_selected(self._builder.tvs_problems):
                self._set_problem(problem)
        except errors.InvalidProblem as ex:
            self._remove_problem_from_storage(ex.problem_id)
            logging.debug(ex.message)

    def _reload_problems(self, source):
        self._reloading = True
        old_selection = self._get_selected(self._builder.tvs_problems)
        canselect = False
        try:
            self._builder.ls_problems.clear()
            prblms = source.get_problems()
            # Can select a problem only if at least one problem was added to
            # the storage
            for p in prblms:
                canselect |= self._add_problem_to_storage(p)
        finally:
            self._reloading = False

        if canselect:
            model = self._builder.tv_problems.get_model()
            pit = None
            if old_selection:
                pit = self._find_problem_iter(old_selection[0], model)

            if pit is None:
                pit = model.get_iter_first()

            if pit is not None:
                self._select_problem_iter(pit)
                return

        self._set_problem(None)

    def _select_problem_by_id(self, problem_id):
        pit = self._find_problem_iter(problem_id,
                self._builder.tv_problems.get_model())
        if pit:
            self._select_problem_iter(pit)
        else:
            logging.debug("Can't select problem id '{0}' because the id was "
                    "not found".format(problem_id))

    def _select_problem_iter(self, pit):
        self._reloading = True
        try:
            self._builder.tvs_problems.unselect_all()
        finally:
            self._reloading = False

        path = self._builder.tv_problems.get_model().get_path(pit)
        if not path:
            logging.debug("Can't select problem because the passed iter can't"
                    " be converted to a tree path")
            return

        self._builder.tvs_problems.select_iter(pit)
        self._builder.tv_problems.scroll_to_cell(path)

    def _show_problem_links(self, submissions):
        need_align = False
        for sbm in submissions:
            if problems.Problem.Submission.URL == sbm.rtype:
                lnk = Gtk.LinkButton(sbm.data, sbm.title)
                lnk.set_visible(True)
                lnk.set_halign(Gtk.Align.START)
                lnk.set_valign(Gtk.Align.START)

                self._builder.vbx_links.pack_start(lnk, False, True, 0)
                need_align = True

        if need_align:
            space = Gtk.Alignment()
            space.set_visible(True)
            space.set_vexpand(True)
            self._builder.vbx_links.pack_start(space, False, True, 0)

    def _show_problem_message(self, message):
        msg = Gtk.Label()
        msg.set_markup(message)
        msg.set_visible(True)
        msg.set_halign(Gtk.Align.START)
        msg.set_valign(Gtk.Align.START)
        msg.set_line_wrap(True)

        self._builder.vbx_problem_messages.pack_start(msg, False, True, 0)

    def _set_problem(self, problem):
        try:
            self.selected_problem = problem

            sensitive_btn = problem is not None
            self._builder.btn_delete.set_sensitive(sensitive_btn)
            self._builder.btn_report.set_sensitive(
                    sensitive_btn and not problem['not-reportable'] )
            self._builder.btn_detail.set_sensitive(sensitive_btn)
            self._builder.vbx_links.foreach(
                    lambda w, u: w.destroy(), None)
            self._builder.vbx_problem_messages.foreach(
                    lambda w, u: w.destroy(), None)

            if problem:
                self._builder.nb_problem_layout.set_current_page(0)
                app = problem['application']
                self._builder.lbl_summary.set_text(problem['reason'] or "")
                self._builder.lbl_app_name_value.set_text(app.name or _("N/A"))
                self._builder.lbl_reason.set_text("{0} {1}".format(
                            app.name or _("N/A"), _(' crashed').strip()))
                self._builder.lbl_app_version_value.set_text(
                            problem['package'] or "")
                self._builder.lbl_detected_value.set_text(
                            problem['date'].strftime(
                                locale.nl_langinfo(locale.D_FMT)))

                if app.icon:
                    self._builder.img_app_icon.set_from_pixbuf(app.icon)
                else:
                    self._builder.img_app_icon.clear()

                if problem['is_reported']:
                    self._builder.lbl_reported_value.set_text(_('yes'))
                    self._show_problem_links(problem['submission'])
                else:
                    self._builder.lbl_reported_value.set_text(_('no'))

                if problem['not-reportable']:
                    self._show_problem_message(problem['not-reportable'])
                elif (not problem['is_reported']
                        or not any((s.name == "Bugzilla"
                                for s in problem['submission']))):
                    self._show_problem_message(
    _("This problem hasn't been reported to <i>Bugzilla</i> yet. "
        "Our developers may need more information to fix the problem.\n"
        "Please consider <b>reporting it</b> - you may help them. Thank you."))
            else:
                self._builder.nb_problem_layout.set_current_page(1)
        except errors.InvalidProblem as ex:
            self._remove_problem_from_storage(ex.problem_id)
            logging.debug(ex.message)

    def _get_selected(self, selection):
        model, rows = selection.get_selected_rows()

        if not rows:
            return []

        return [model[p][2] for p in rows]

    def on_tvs_problems_changed(self, selection):
        if not self._reloading:
            selection = self._get_selected(selection)
            if selection:
                self._set_problem(selection[0])
                return

            pit = self._builder.tv_problems.get_model().get_iter_first()
            if pit:
                self._select_problem_iter(pit)
                return

            # Clear window because of empty list of problems!
            self._set_problem(None)

    def on_gac_delete_activate(self, action):
        try:
            for prblm in self._get_selected(self._builder.tvs_problems):
                self._controller.delete(prblm)
        except errors.InvalidProblem as ex:
            self._remove_problem_from_storage(ex.problem_id)
            logging.debug(ex.message)

    def on_gac_detail_activate(self, action):
        try:
            selected = self._get_selected(self._builder.tvs_problems)
            if selected:
                self._controller.detail(selected[0])
        except errors.InvalidProblem as ex:
            self._remove_problem_from_storage(ex.problem_id)
            logging.debug(ex.message)

    def on_gac_report_activate(self, action):
        try:
            selected = self._get_selected(self._builder.tvs_problems)
            if selected and not selected[0]['not-reportable']:
                self._controller.report(selected[0])
        except errors.InvalidProblem as ex:
            self._remove_problem_from_storage(ex.problem_id)
            logging.debug(ex.message)

    def on_te_search_changed(self, entry):
        try:
            self._filter.set_pattern(entry.get_text())
        except errors.InvalidProblem as ex:
            self._remove_problem_from_storage(ex.problem_id)
            logging.debug(ex.message)

    def on_gac_opt_all_problems_activate(self, action):
        conf = config.get_configuration()
        conf['all_problems'] = self._builder.chb_all_problems.get_active()

    def on_gac_control_preferences_activate(self, action):
        wrappers.show_events_list_dialog(self)

    def on_gac_open_directory_activate(self, action):
        selection = self._get_selected(self._builder.tvs_problems)
        if selection:
            subprocess.call(["xdg-open", selection[0].problem_id])
        self._builder.menu_problem_item.popdown()

    def on_gac_copy_id_activate(self, action):
        selection = self._get_selected(self._builder.tvs_problems)
        if selection:
            (Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                .set_text(selection[0].problem_id, -1))
        self._builder.menu_problem_item.popdown()

    def on_tv_problems_button_press_event(self, sender, data):
        # getattribute() used because number as first character in name
        # is syntax error
        if (data.type == type.__getattribute__(Gdk.EventType, '2BUTTON_PRESS')
                and data.button == Gdk.BUTTON_PRIMARY):
            self._builder.gac_report.activate()
        elif (data.type == Gdk.EventType.BUTTON_PRESS
                and data.button == Gdk.BUTTON_SECONDARY):
            pos = self._builder.tv_problems.get_path_at_pos(data.x, data.y)
            if pos:
                self._builder.menu_problem_item.popup(None, None, None, None,
                        data.button, data.time)
