#!/usr/bin/env python
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

from gi.repository import Gtk
from gi.repository import Gdk

import problems
import config
import wrappers
from tools import fancydate
from l10n import _, GETTEXT_PROGNAME
import errors

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
        super(OopsWindow, self).__init__(title=_('Automatic Bug Reporting Tool'), application=application)

        self.set_default_size(780, 480)

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


        self._source_observer = SourceObserver(self)
        self._source.attach(self._source_observer)

        self.tv_problems.grab_focus()
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
        self.btn_delete = builder.get_object('btn_delete')
        self.btn_report = builder.get_object('btn_report')
        self.te_search = builder.get_object('te_search')
        self.chb_all_problems = builder.get_object('chb_all_problems')
        self.vbx_links = builder.get_object('vbx_links')
        self.vbx_problem_messages = builder.get_object('vbx_problem_messages')
        self.gac_report = builder.get_object('gac_report')
        self.gac_delete = builder.get_object('gac_delete')

        gv_links = builder.get_object('gv_links')
        stl_ctx = gv_links.get_style_context()
        css_prv = Gtk.CssProvider()
        css_prv.load_from_data("GtkViewport {\n"
                               "  background-color : @theme_bg_color;\n"
                               "}\n")
        stl_ctx.add_provider(css_prv, 6000)

        self.ag_accelerators = Gtk.AccelGroup()
        self.ag_accelerators.connect_by_path(self.gac_report.get_accel_path(), lambda *args: self.gac_report.activate())
        self.ag_accelerators.connect_by_path(self.gac_delete.get_accel_path(), lambda *args: self.gac_delete.activate())
        self.add_accel_group(self.ag_accelerators)

        builder.connect_signals(self)

    def _find_problem_iter(self, problem, model):
        pit = model.get_iter_first()
        while pit:
            if model[pit][2] == problem:
                return pit
            pit = model.iter_next(pit)

        return None

    def _add_problem_to_storage(self, problem):
        try:
            self.ls_problems.append(problem_to_storage_values(problem))
        except InvalidProblem as ex:
            logging.debug(ex.message)

    def _remove_problem_from_storage(self, problem):
        pit = self._find_problem_iter(problem, self.ls_problems)
        if pit:
            self.ls_problems.remove(pit)

    def _update_problem_in_storage(self, problem):
        pit = self._find_problem_iter(problem, self.ls_problems)
        if pit:
            try:
                values = problem_to_storage_values(problem)
                for i in xrange(0, len(values)-1):
                    self.ls_problems.set_value(pit, i, values[i])
            except InvalidProblem as ex:
                self._remove_problem_from_storage(problem)
                logging.debug(ex.message)
                return

        if problem == self._get_selected(self.tvs_problems):
            self._set_problem(problem)

    def _reload_problems(self, source):
        self._reloading = True
        old = self._get_selected(self.tvs_problems);
        try:
            self.ls_problems.clear()
            problems = source.get_problems()
            for p in problems:
                self._add_problem_to_storage(p)
        finally:
            self._reloading = False

        if len(problems) > 0:
            if old:
                pit = self._find_problem_iter(old, self.tv_problems.get_model())
                if pit:
                    self._select_problem_iter(pit)
                    return

            self._select_problem_iter(self.tv_problems.get_model().get_iter_first())
        else:
            self._set_problem(None)

    def _select_problem_by_id(self, problem_id):
        pit = self._find_problem_iter(problem_id, self.tv_problems.get_model())
        if pit:
            self._select_problem_iter(pit)
        else:
            logging.debug("Can't select problem id '{0}' because the id was not found".format(problem_id))

    def _select_problem_iter(self, pit):
         self._reloading = True
         self.tvs_problems.unselect_all()
         self._reloading = False
         path = self.tv_problems.get_model().get_path(pit)
         if not path:
            logging.debug("Can't select problem because the passed iter can't be converted to a tree path");
            return

         self.tvs_problems.select_iter(pit)
         self.tv_problems.scroll_to_cell(path)

    def _show_problem_links(self, submissions):
        need_align = False
        for s in submissions:
            if problems.Problem.Submission.URL == s.rtype:
                lnk = Gtk.LinkButton(s.data, s.title)
                lnk.set_visible(True)
                lnk.set_halign(Gtk.Align.START)
                lnk.set_valign(Gtk.Align.START)

                self.vbx_links.pack_start(lnk, False, True, 0)
                need_align = True

        if need_align:
            space = Gtk.Alignment()
            space.set_visible(True)
            space.set_vexpand(True)
            self.vbx_links.pack_start(space, False, True, 0)

    def _show_problem_message(self, message):
        msg = Gtk.Label()
        msg.set_markup(message)
        msg.set_visible(True)
        msg.set_halign(Gtk.Align.START)
        msg.set_valign(Gtk.Align.START)
        msg.set_line_wrap(True)

        self.vbx_problem_messages.pack_start(msg, False, True, 0)

    def _set_problem(self, problem):
        try:
            self.selected_problem = problem

            sensitive_btn = not problem is None
            self.btn_delete.set_sensitive(sensitive_btn)
            self.btn_report.set_sensitive(not problem is None and not problem['not-reportable'] )
            self.vbx_links.foreach(lambda w, u: w.destroy(), None)
            self.vbx_problem_messages.foreach(lambda w, u: w.destroy(), None)

            if problem:
                self.nb_problem_layout.set_current_page(0)
                app = problem['application']
                self.lbl_reason.set_text("{0} {1}".format(doN(app.name, _("N/A")), _(' crashed').strip()));
                self.lbl_summary.set_text(doN(problem['reason'], ""))
                self.lbl_app_name_value.set_text(doN(app.name, _("N/A")))
                self.lbl_app_version_value.set_text(doN(problem['package'], ""))

                if app.icon:
                    self.img_app_icon.set_from_pixbuf(app.icon)
                else:
                    self.img_app_icon.clear()

                if problem['is_reported']:
                    self.lbl_reported_value.set_text(_('yes'))
                    self._show_problem_links(problem['submission'])
                else:
                    self.lbl_reported_value.set_text(_('no'))

                if problem['not-reportable']:
                    self._show_problem_message(problem['not-reportable'])
                elif not problem['is_reported'] or not any((s.title == "Bugzilla" for s in problem['submission'])):
                    self._show_problem_message(_("This problem hasn't been reported to <i>Bugzilla</i> yet,"\
                                "our developers maybe need more information to sort out the problem.\n"\
                                "Please consider <b>reporting it</b>, you may help them. Thank you."))
            else:
                self.nb_problem_layout.set_current_page(1)
        except errors.InvalidProblem as ex:
            logging.debug(ex.message)
            self._source.refresh()

    def _get_selected(self, selection, only_first=True):
        model, rows = selection.get_selected_rows()

        if only_first:
            if not rows:
                return None

            return model[rows[0]][2]

        if not rows:
            return []

        return [model[p][2] for p in rows]

    def on_tvs_problems_changed(self, selection):
        if not self._reloading:
            p = self._get_selected(selection)
            if p:
                self._set_problem(p)
                return

            pit = self.tv_problems.get_model().get_iter_first()
            if pit:
                self._select_problem_iter(pit);
                return

            # Clear window because of empty list of problems!
            self._set_problem(None)

    def on_gac_delete_activate(self, action):
        for p in self._get_selected(self.tvs_problems, False):
            self._controller.delete(p)

    def on_gac_detail_activate(self, action):
        selected = self._get_selected(self.tvs_problems)
        if selected:
            self._controller.detail(selected)

    def on_gac_report_activate(self, action):
        selected = self._get_selected(self.tvs_problems)
        if selected and not selected['not-reportable']:
            self._controller.report(selected)

    def on_te_search_changed(self, entry):
        self._filter.set_pattern(entry.get_text())

    def on_gac_opt_all_problems_activate(self, action):
        conf = config.get_configuration()
        conf['all_problems'] = self.chb_all_problems.get_active()

    def on_gac_control_preferences_activate(self, action):
        wrappers.show_events_list_dialog(self)

    def on_wnd_main_button_press_event(self, button):
        print "press"
        self.gm_control.poppup()

    def on_tv_problems_button_press_event(self, sender, e):
        if e.type == type.__getattribute__(Gdk.EventType, '2BUTTON_PRESS'):
            self.gac_report.activate()
