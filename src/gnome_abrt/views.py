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
import traceback
import datetime

#pygobject
import gi
#pylint: disable=E0611
from gi.repository import Gtk
#pylint: disable=E0611
from gi.repository import Gdk
#pylint: disable=E0611
from gi.repository import GObject
#pylint: disable=E0611
from gi.repository import Gio
#pylint: disable=E0611
from gi.repository import Pango
#pylint: disable=E0611
from gi.repository import GLib

import humanize

from gnome_abrt import problems, config, wrappers, errors
from gnome_abrt.tools import fancydate, smart_truncate, load_icon
from gnome_abrt.tools import set_icon_from_pixbuf_with_scale
from gnome_abrt.l10n import _, C_, GETTEXT_PROGNAME

gi.require_version('Gtk', '3.0')

class ProblemsFilter:

    def __init__(self, list_box, list_box_selection):
        self._pattern = ""
        self._list_box = list_box
        self._list_box.set_filter_func(lambda row, _: self.match(row), None)
        self._list_box_selection = list_box_selection

    def set_pattern(self, pattern):
        self._pattern = pattern
        self._list_box.invalidate_filter()

        i = 0
        problem_row = self._list_box.get_row_at_index(i)
        while problem_row is not None:
            if self.match(problem_row):
                self._list_box.select_row(problem_row)
                break

            i += 1
            problem_row = self._list_box.get_row_at_index(i)

        if problem_row is None:
            self._list_box_selection.unselect_all()

    def match(self, list_box_row):
        # None nevere matches the patter
        if list_box_row is None:
            return False

        # Empty string mathces everything
        if not self._pattern:
            return True

        problem = list_box_row.get_problem()

        for i in ['component', 'reason', 'executable', 'package']:
            if problem[i] is None:
                logging.debug("Problem '{0}' doesn't have '{1}'"
                                .format(problem.problem_id, i))
                continue

            # _pattern is 'ascii' and problem[i] is 'dbus.String'
            val = str(problem[i])
            if val and self._pattern in val:
                return True

        # Check Bug tracker ID
        if problem['is_reported']:
            for sbm in problem['submission']:
                if problems.Problem.Submission.URL != sbm.rtype:
                    continue

                # _pattern is 'str' and sbm.data is 'dbus.String', so we need
                # to convert sbm.data to a regular 'str'
                rid = str(sbm.data)
                rid = rid.rstrip('/').split('/')[-1].split('=')[-1]
                if self._pattern in rid:
                    return True

        # This might be confusing as users can't see problem ID in UI but it
        # will come in handy when you want to see particular problem discovered
        # in the system logs.
        if self._pattern in problem.problem_id:
            return True

        app = problem['application']
        if app is None or app.name is None:
            return False

        return self._pattern in app.name


def problem_to_storage_values(problem):
    app = problem.get_application()

    if app.name:
        name = app.name
    else:
        name = problem['human_type']

    if name == "kernel" or name.startswith("kernel-"):
        # Translators: if the kernel crashed we display the word "System"
        # instead of "kernel". In this context "System" is like a proper
        # package name, probably a nominative noun.
        name = C_("package name", "System")

    problem_type = problem['type']
    if problem_type == "CCpp":
        # Translators: These are the problem types displayed in the problem
        # list under the application name
        problem_type = _("Application Crash")
    elif problem_type == "vmcore":
        problem_type = _("System Crash")
    elif problem_type == "Kerneloops":
        problem_type = _("System Failure")
    else:
        problem_type = _("Misbehavior")

    return (smart_truncate(name, length=40),
            fancydate(problem['date_last']),
            problem_type,
            problem['count'],
            problem)


#pylint: disable=W0613
def time_sort_func(first_row, second_row, trash):
    fst_problem = first_row.get_problem()
    scn_problem = second_row.get_problem()
    # skip invalid problems which were marked invalid while sorting
    if (fst_problem.problem_id in trash or
        scn_problem.problem_id in trash):
        return 0

    try:
        lhs = fst_problem['date_last'].timetuple()
        rhs = scn_problem['date_last'].timetuple()
        return time.mktime(rhs) - time.mktime(lhs)
    except errors.InvalidProblem as ex:
        trash.add(ex.problem_id)
        logging.debug(ex)
        return 0

def format_button_source_name(name, source):
    return "{0} ({1})".format(name, len(source.get_problems()))


def handle_problem_and_source_errors(func):
    """Wraps repetitive exception handling."""

    def wrapper_for_instance_function(oops_wnd, *args):
        try:
            return func(oops_wnd, *args)
        except errors.InvalidProblem as ex:
            logging.debug(traceback.format_exc())
            oops_wnd._remove_problem_from_storage(ex.problem_id)
        except errors.UnavailableSource as ex:
            logging.debug(traceback.format_exc())
            oops_wnd._disable_source(ex.source, ex.temporary)

        return None

    return wrapper_for_instance_function


class ListBoxSelection:

    def __init__(self, list_box, selection_changed):
        self._lb = list_box

        self._lb.connect('selected-rows-changed', self._on_row_selected)

        self._selection = []
        self._selection_changed = selection_changed

    def _on_row_selected(self, _):
        self._selection_changed(self)

    def unselect_all(self):
        if self._lb.get_selection_mode() == Gtk.SelectionMode.MULTIPLE:
            self._lb.unselect_all()
        else:
            selected_row = self._lb.get_selected_row()
            if selected_row is not None:
                self._lb.unselect_row(selected_row)

        self._lb.unselect_all()

    def get_selected_rows(self):
        return [lbr.get_problem() for lbr in self._lb.get_selected_rows()]


class ProblemRow(Gtk.ListBoxRow):

    def __init__(self, problem_values):
        super().__init__()

        self._problem = problem_values[4]

        grid = Gtk.Grid.new()

        self.add(grid)

        self._lbl_app = Gtk.Label.new(problem_values[0])
        self._lbl_app.set_halign(Gtk.Align.START)
        self._lbl_app.set_hexpand(True)
        self._lbl_app.set_alignment(0.0, 0.5)
        self._lbl_app.set_ellipsize(Pango.EllipsizeMode.END)
        self._lbl_app.set_width_chars(15)
        self._lbl_app.get_style_context().add_class('app-name-label')

        grid.attach_next_to(self._lbl_app, None, Gtk.PositionType.RIGHT, 1, 1)

        self._lbl_date = Gtk.Label.new(problem_values[1])
        self._lbl_date.set_halign(Gtk.Align.END)
        self._lbl_date.get_style_context().add_class('dim-label')

        grid.attach_next_to(self._lbl_date, self._lbl_app, Gtk.PositionType.RIGHT, 1, 1)

        self._lbl_type = Gtk.Label.new(problem_values[2])
        self._lbl_type.set_halign(Gtk.Align.START)
        self._lbl_type.set_hexpand(True)
        self._lbl_type.set_alignment(0.0, 0.5)
        self._lbl_type.get_style_context().add_class('dim-label')

        grid.attach_next_to(self._lbl_type, self._lbl_app, Gtk.PositionType.BOTTOM, 1, 1)

        self._lbl_count = Gtk.Label.new(problem_values[3])
        self._lbl_count.set_halign(Gtk.Align.END)
        self._lbl_count.get_style_context().add_class('dim-label')

        grid.attach_next_to(self._lbl_count, self._lbl_type, Gtk.PositionType.RIGHT, 1, 1)

        self.show_all()

    def set_values(self, problem_values):
        self._lbl_app.set_text(problem_values[0])
        self._lbl_date.set_text(problem_values[1])
        self._lbl_type.set_text(problem_values[2])
        self._lbl_count.set_text(problem_values[3])
        self._problem = problem_values[4]

    def get_problem(self):
        return self._problem


#pylint: disable=R0902
@Gtk.Template(resource_path='/org/freedesktop/GnomeAbrt/ui/oops-window.ui')
class OopsWindow(Gtk.ApplicationWindow):

    __gtype_name__ = 'OopsWindow'

    header_bar = Gtk.Template.Child()
    box_header_left = Gtk.Template.Child()
    box_sources_switcher = Gtk.Template.Child()
    box_panel_left = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    lbl_reason = Gtk.Template.Child()
    lbl_summary = Gtk.Template.Child()
    lbl_app_name_value = Gtk.Template.Child()
    lbl_app_version_value = Gtk.Template.Child()
    lbl_detected_value = Gtk.Template.Child()
    lbl_reported = Gtk.Template.Child()
    lbl_reported_value = Gtk.Template.Child()
    lb_problems = Gtk.Template.Child()
    img_app_icon = Gtk.Template.Child()
    nb_problem_layout = Gtk.Template.Child()
    btn_delete = Gtk.Template.Child()
    btn_report = Gtk.Template.Child()
    app_menu_button = Gtk.Template.Child()
    btn_detail = Gtk.Template.Child()
    vbx_links = Gtk.Template.Child()
    vbx_problem_messages = Gtk.Template.Child()
    tbtn_multi_select = Gtk.Template.Child()
    gd_problem_info = Gtk.Template.Child()
    vbx_empty_page = Gtk.Template.Child()
    vbx_no_source_page = Gtk.Template.Child()

    def placeholder_mapped(self, label, data):
        self.tbtn_multi_select.set_sensitive(False)

    def placeholder_unmapped(self, label, data):
        self.tbtn_multi_select.set_sensitive(True)

    class SourceObserver:
        def __init__(self, wnd):
            self.wnd = wnd
            self._enabled = True

        def enable(self):
            self._enabled = True

        def disable(self):
            self._enabled = False

        def changed(self, source, change_type=None, problem=None):
            if not self._enabled:
                return

            try:
                if source == self.wnd._source:
                    if change_type is None:
                        self.wnd._reload_problems(source)
                    elif change_type == problems.ProblemSource.NEW_PROBLEM:
                        self.wnd._add_problem_to_storage(problem)
                    elif change_type == problems.ProblemSource.DELETED_PROBLEM:
                        self.wnd._remove_problem_from_storage(problem)
                    elif change_type == problems.ProblemSource.CHANGED_PROBLEM:
                        self.wnd._update_problem_in_storage(problem)

                self.wnd._update_source_button(source)
            except errors.UnavailableSource as ex:
                self.wnd._disable_source(ex.source, ex.temporary)


    class OptionsObserver:
        def __init__(self, wnd):
            self.wnd = wnd

        def option_updated(self, conf, option):
            if option == 'problem' and conf[option]:
                self.wnd._select_problem_by_id(conf[option])
            if option == 'T_FMT' and conf[option]:
                self.wnd._reload_problems(self.wnd._source)
            if option == 'D_T_FMT' and conf[option]:
                self.wnd._set_problem(self.wnd.selected_problem)


    def __init__(self, application, sources, controller):
        super().__init__(application=application)

        if not sources:
            raise ValueError("The source list cannot be empty!")

        label = Gtk.Label.new('')
        label.show()
        self.lb_problems.set_placeholder(label)
        label.connect('map', self.placeholder_mapped, self)
        label.connect('unmap', self.placeholder_unmapped, self)

        builder = Gtk.Builder()
        builder.set_translation_domain(GETTEXT_PROGNAME)
        builder.add_from_resource('/org/freedesktop/GnomeAbrt/ui/oops-menus.ui')

        self.app_menu_button.set_menu_model(builder.get_object('app_menu'))

        self.menu_problem_item = builder.get_object('menu_problem_item')
        self.menu_problem_item = Gtk.Menu.new_from_model(self.menu_problem_item)

        self.menu_problem_item.attach_to_widget(self)

        self.menu_multiple_problems = builder.get_object(
                'menu_multiple_problems')
        self.menu_multiple_problems = Gtk.Menu.new_from_model(
                self.menu_multiple_problems)

        self.menu_multiple_problems.attach_to_widget(self)

        #pylint: disable=E1120
        css_prv = Gtk.CssProvider.new()
        css_prv.load_from_resource('/org/freedesktop/GnomeAbrt/css/oops.css')
        stl_ctx = self.get_style_context()
        stl_ctx.add_provider_for_screen(stl_ctx.get_screen(), css_prv, 6000)

        self._source_observer = OopsWindow.SourceObserver(self)
        self._source_observer.disable()

        self._reloading = False
        self._controller = controller

        self.selected_problem = None
        self._all_sources = []
        self._source = None
        self._handling_source_click = False
        self._configure_sources(sources)
        self._set_button_toggled(self._source.button, True)

        # a set where invalid problems found while sorting of the problem list
        # are stored
        self._trash = set()
        self.lb_problems.set_sort_func(time_sort_func, self._trash)
        self.lss_problems = ListBoxSelection(self.lb_problems,
                self.on_tvs_problems_changed)
        self._filter = ProblemsFilter(self.lb_problems,
                self.lss_problems)

        self.lb_problems.grab_focus()
        try:
            self._reload_problems(self._source)
        except errors.UnavailableSource as ex:
            self._disable_source(ex.source, ex.temporary)

        self._options_observer = OopsWindow.OptionsObserver(self)
        conf = config.get_configuration()
        conf.set_watch('problem', self._options_observer)
        conf.set_watch('T_FMT', self._options_observer)
        conf.set_watch('D_T_FMT', self._options_observer)
        self._options_observer.option_updated(conf, 'problem')

        # enable observer
        self._source_observer.enable()

        self.lb_problems.connect("key-press-event", self._on_key_press_event)

        self._add_actions(application)


    def _add_actions(self, application):
        action = Gio.SimpleAction.new('delete', None)
        action.connect('activate', self.on_gac_delete_activate)
        self.add_action(action)

        application.set_accels_for_action('win.delete', ['Delete'])

        action = Gio.SimpleAction.new('report', None)
        action.connect('activate', self.on_gac_report_activate)
        self.add_action(action)

        application.set_accels_for_action('win.report', ['Return'])

        action = Gio.SimpleAction.new('details', None)
        action.connect('activate', self.on_gac_detail_activate)
        self.add_action(action)

        application.set_accels_for_action('win.details', ['<Primary>Return'])

        action = Gio.SimpleAction.new('open-directory', None)
        action.connect('activate', self.on_gac_open_directory_activate)
        self.add_action(action)

        application.set_accels_for_action('win.open-directory', ['<Primary>o'])

        action = Gio.SimpleAction.new('copy-id', None)
        action.connect('activate', self.on_gac_copy_id_activate)
        self.add_action(action)

        application.set_accels_for_action('win.copy-id', ['<Primary>c'])

        action = Gio.SimpleAction.new('search', None)
        action.connect('activate', self.on_gac_search_activate)
        self.add_action(action)

        application.set_accels_for_action('win.search', ['<Primary>f'])

    def _configure_sources(self, sources):
        for name, src in sources:
            self._all_sources.append(src)
            src.attach(self._source_observer)

            label = None
            try:
                label = format_button_source_name(name, src)
            except errors.UnavailableSource:
                logging.debug("Unavailable source: {0}".format(name))
                continue

            src_btn = Gtk.ToggleButton.new_with_label(label)
            src_btn.set_visible(True)
            # add an extra member source (I don't like it but it so easy)
            src_btn.source = src
            self.box_sources_switcher.pack_start(src_btn, False, True, 0)

            # add an extra member name (I don't like it but it so easy)
            src.name = name
            # add an extra member button (I don't like it but it so easy)
            src.button = src_btn
            src_btn.connect("clicked", self._on_source_btn_clicked, src)

        self._source = self._all_sources[0]

    def _update_source_button(self, source):
        name = format_button_source_name(source.name, source)
        source.button.set_label(name)

    def _set_button_toggled(self, button, state):
        # set_active() triggers the clicked signal
        # and if we set the active in program,
        # we don't want do any action in the clicked handler
        self._handling_source_click = True
        try:
            button.set_active(state)
        finally:
            self._handling_source_click = False

    def _on_source_btn_clicked(self, btn, args):
        # If True, then button's state was not changed by click
        # and we don't want to switch source
        if self._handling_source_click:
            return

        res, old_source = self._switch_source(btn.source)
        if not res:
            # switching sources failed and we have to untoggle clicked
            # source's button
            self._set_button_toggled(btn, False)
        else:
            if old_source is not None:
                # sources were switched and we have to untoggle old source's
                # button
                self._set_button_toggled(old_source.button, False)
            elif not btn.get_active():
                # source wasn't changed and we have to set toggled back if
                # someone clicked already selected button
                self._set_button_toggled(btn, True)

    def _switch_source(self, source):
        """Sets the passed source as the selected source."""

        result = True
        old_source = None
        if source != self._source:
            try:
                self._reload_problems(source)
                old_source = self._source
                self._source = source
            except errors.UnavailableSource as ex:
                self._disable_source(source, ex.temporary)
                result = False

        return (result, old_source)

    def _disable_source(self, source, temporary):
        if self._source is None or not self._all_sources:
            return

        # Some sources can be components of other sources.
        # Problems are connected directly to the component sources, therefore
        # exception's source is a component source, thus we have to find an
        # instance of composite source which the unavailable component source
        # belongs.
        source_index = self._all_sources.index(source)

        if source_index != -1:
            real_source = self._all_sources[source_index]
            self._set_button_toggled(real_source.button, False)
            if not temporary:
                logging.debug("Disabling source")
                real_source.button.set_sensitive(False)
                self._all_sources.pop(source_index)

        if source != self._source:
            return

        # We just disabled the currently selected source. So, we should select
        # some other source. The simplest way is to select the first source
        # but only if it is not the disabled source.
        # If the disabled source is completely unavailable (not temporary) we
        # can always select the source at index 0 because the disabled
        # source was removed from the _all_sources list.
        if (not temporary or source_index != 0) and self._all_sources:
            self._source = self._all_sources[0]
            self._set_button_toggled(self._source.button, True)
        else:
            self._source = None

        try:
            self._reload_problems(self._source)
        except errors.UnavailableSource as ex:
            self._disable_source(ex.source, ex.temporary)

    @handle_problem_and_source_errors
    def _find_problem_row_full(self, problem):
        i = 0
        lb_row = self.lb_problems.get_row_at_index(i)
        while lb_row is not None:
            if problem == lb_row.get_problem():
                break

            i += 1
            lb_row = self.lb_problems.get_row_at_index(i)

        return (i, lb_row)

    @handle_problem_and_source_errors
    def _find_problem_row(self, problem):
        return self._find_problem_row_full(problem)[1]

    def _add_problem_to_storage(self, problem):
        try:
            values = problem_to_storage_values(problem)
        except errors.InvalidProblem:
            logging.debug("Exception: {0}".format(traceback.format_exc()))
            return

        self._append_problem_values_to_storage(values)

    def _append_problem_values_to_storage(self, problem_values):
        problem_cell = ProblemRow(problem_values)
        self.lb_problems.insert(problem_cell, -1)
        self._clear_invalid_problems_trash()

    def _clear_invalid_problems_trash(self):
        # append methods trigger time_sort_func() where InvalidProblem
        # exception can occur. In that case time_sort_func() pushes an invalid
        # problem to the trash set because the invalid problem cannot be
        # removed while executing the operation
        while self._trash:
            self._remove_problem_from_storage(self._trash.pop())

    def _remove_problem_from_storage(self, problem):
        if problem is None:
            return

        index, problem_row = self._find_problem_row_full(problem)
        if problem_row is None:
            return

        selected = problem in self._get_selected(self.lss_problems)

        problem_row.destroy()

        if selected:
            for i in range(index, -1, -1):
                problem_row = self.lb_problems.get_row_at_index(i)
                if self._filter.match(problem_row):
                    break

            if problem_row is not None:
                self.lb_problems.select_row(problem_row)
            else:
                self._set_problem(None)

    def _update_problem_in_storage(self, problem):
        problem_row = self._find_problem_row(problem)
        if problem_row is not None:
            try:
                values = problem_to_storage_values(problem)
            except errors.InvalidProblem as ex:
                logging.debug("Exception: {0}".format(traceback.format_exc()))
                self._remove_problem_from_storage(ex.problem_id)
                return

            problem_row.set_values(values)
            self.lb_problems.invalidate_sort()
            self._clear_invalid_problems_trash()

        if problem in self._get_selected(self.lss_problems):
            self._set_problem(problem)

    def _reload_problems(self, source):
        # Try to load and prepare the list of selected problems before we
        # clear the view. So, we can gracefully handle UnavailableSource
        # exception. If the reloaded source is unavailable the old list
        # of problems remains untouched.
        storage_problems = []
        if source is not None:
            prblms = source.get_problems()
            for p in prblms:
                try:
                    storage_problems.append(problem_to_storage_values(p))
                except errors.InvalidProblem:
                    logging.debug("Exception: {0}"
                            .format(traceback.format_exc()))

        old_selection = self._get_selected(self.lss_problems)

        self._reloading = True
        try:
            self.lb_problems.foreach(lambda w, u: w.destroy(), None)

            if storage_problems:
                for p in storage_problems:
                    self._append_problem_values_to_storage(p)
        finally:
            self._reloading = False

        if storage_problems:
            problem_row = None
            if old_selection:
                problem_row = self._find_problem_row(old_selection[0])

            i = 0
            if problem_row is None:
                problem_row = self.lb_problems.get_row_at_index(i)
                i = 1

            while (problem_row is not None
                    and not self._filter.match(problem_row)):
                problem_row = self.lb_problems.get_row_at_index(i)
                i += 1

            if problem_row is not None:
                self.lb_problems.select_row(problem_row)
                return

        self._set_problem(None)

    def _select_problem_by_id(self, problem_id):
        # The problem could come from a different source than the currently
        # loaded source. If so, try to switch to problem's origin source and
        # select the problem after that.
        if (self._source is not None and
                problem_id not in self._source.get_problems()):
            for source in self._all_sources:
                if problem_id in source.get_problems():
                    res, old_source = self._switch_source(source)
                    if res:
                        self._set_button_toggled(old_source.button, False)
                        self._set_button_toggled(source.button, True)
                    break

        problem_row = self._find_problem_row(problem_id)

        if problem_row is not None:
            self.lb_problems.select_row(problem_row)
        else:
            logging.debug("Can't select problem id '{0}' because the id was "
                    "not found".format(problem_id))

    def _show_problem_links(self, submissions):
        if not submissions:
            return False

        link_added = False
        for sbm in submissions:
            if problems.Problem.Submission.URL == sbm.rtype:
                lnk = Gtk.Label.new(sbm.title)
                lnk.set_use_markup(True)
                lnk.set_markup(
                    "<a href=\"{0}\">{1}</a>".format(sbm.data, sbm.title))
                lnk.set_halign(Gtk.Align.START)
                lnk.set_line_wrap(True)
                lnk.set_visible(True)

                self.vbx_links.pack_start(lnk, False, True, 0)
                link_added = True

        return link_added

    def _show_problem_message(self, message):
        msg = Gtk.Label.new(message)
        msg.set_markup(message)
        msg.set_visible(True)
        msg.set_halign(Gtk.Align.START)
        msg.set_valign(Gtk.Align.START)
        msg.set_line_wrap(True)
        msg.set_selectable(True)
        msg.set_xalign(0)

        self.vbx_problem_messages.pack_start(msg, False, True, 0)

    @handle_problem_and_source_errors
    def _set_problem(self, problem):
        def destroy_links(widget, _):
            if widget != self.lbl_reported_value:
                widget.destroy()

        self.selected_problem = problem

        sensitive_btn = problem is not None
        self.btn_delete.set_sensitive(sensitive_btn)
        self.btn_report.set_sensitive(sensitive_btn and not problem['not-reportable'])
        self.vbx_links.foreach(destroy_links, None)
        self.vbx_problem_messages.foreach(lambda w, u: w.destroy(), None)

        if problem:
            self.nb_problem_layout.set_visible_child(self.gd_problem_info)
            app = problem['application']
            if problem['type'] == 'Kerneloops':
                self.lbl_reason.set_text(
            _("Unexpected system error"))
                self.lbl_summary.set_text(
            _("The system has encountered a problem and recovered."))
            elif problem['type'] == 'vmcore':
                self.lbl_reason.set_text(
            _("Fatal system failure"))
                self.lbl_summary.set_text(
            _("The system has encountered a problem and could not continue."))
            else:
                if not app.name:
                    self.lbl_reason.set_text(
                            # Translators: If Application's name is unknown,
                            # display neutral header
                            # "'Type' problem has been detected". Examples:
                            #  Kerneloops problem has been detected
                            #  C/C++ problem has been detected
                            #  Python problem has been detected
                            #  Ruby problem has been detected
                            #  VMCore problem has been detected
                            #  AVC problem has been detected
                            #  Java problem has been detected
                            _("{0} problem has been detected").format(
                                    problem['human_type']))
                else:
                    self.lbl_reason.set_text(
                            _("{0} quit unexpectedly").format(app.name))

                self.lbl_summary.set_text(
            _("The application encountered a problem and could not continue."))

            self.lbl_app_name_value.set_text(
                        # Translators: package name not available
                        problem['package_name'] or _("N/A"))
            self.lbl_app_version_value.set_text(
                        # Translators: package version not available
                        problem['package_version'] or _("N/A"))
            self.lbl_detected_value.set_text(
                humanize.naturaltime(datetime.datetime.now()-problem['date']))
            self.lbl_detected_value.set_tooltip_text(
                problem['date'].strftime(config.get_configuration()['D_T_FMT']))

            icon_buf = None
            scale = self.img_app_icon.get_scale_factor()
            if app.icon:
                icon_buf = load_icon(gicon=app.icon, scale=scale)

            if icon_buf is None:
                icon_buf = load_icon(name="system-run-symbolic", scale=scale)
                self.img_app_icon.get_style_context().add_class(
                                                                    'dim-label')
            else:
                self.img_app_icon.get_style_context().remove_class(
                                                                    'dim-label')

            # icon_buf can be None and if it is None, no icon will be displayed
            set_icon_from_pixbuf_with_scale(self.img_app_icon,
                                            icon_buf, scale)

            self.lbl_reported_value.show()
            self.lbl_reported.set_text(_("Reported"))
            if problem['not-reportable']:
                self.lbl_reported_value.set_text(
                        _('cannot be reported'))
                self._show_problem_links(problem['submission'])
                self._show_problem_message(problem['not-reportable'])
            elif problem['is_reported']:
                if self._show_problem_links(problem['submission']):
                    self.lbl_reported.set_text(_("Reports"))
                    self.lbl_reported_value.hide()

                    if (not any((s.name == "Bugzilla"
                                for s in problem['submission']))):
                        self._show_problem_message(
_("This problem has been reported, but a <i>Bugzilla</i> ticket has not"
" been opened. Our developers may need more information to fix the problem.\n"
"Please consider also <b>reporting it</b> to Bugzilla in"
" order to provide that. Thank you."))
                else:
                    # Translators: Displayed after 'Reported' if a problem
                    # has been reported but we don't know where and when.
                    # Probably a rare situation, usually if a problem is
                    # reported we display a list of reports here.
                    self.lbl_reported_value.set_text(_('yes'))
            else:
                # Translators: Displayed after 'Reported' if a problem
                # has not been reported.
                self.lbl_reported_value.set_text(_('no'))
        else:
            if self._source is not None:
                self.nb_problem_layout.set_visible_child(self.vbx_empty_page)
            else:
                self.nb_problem_layout.set_visible_child(self.vbx_no_source_page)

    def _get_selected(self, selection):
        return selection.get_selected_rows()

    @Gtk.Template.Callback()
    def on_tbtn_multi_select_toggled(self, tbtn):
        if tbtn.get_active():
            self.lb_problems.set_selection_mode(
                    Gtk.SelectionMode.MULTIPLE)
            if self.header_bar is not None:
                self.header_bar.get_style_context().add_class(
                                                               'selection-mode')
        else:
            row = self.lb_problems.get_selected_row()
            if row is None:
                row = self.lb_problems.get_row_at_index(0)

            self.lb_problems.set_selection_mode(
                    Gtk.SelectionMode.BROWSE)

            if row is not None and self._filter.match(row):
                self.lb_problems.select_row(row)

            if self.header_bar is not None:
                self.header_bar.get_style_context().remove_class(
                                                               'selection-mode')

    def on_tvs_problems_changed(self, selection):
        if not self._reloading:
            rows = self._get_selected(selection)
            if rows:
                self._set_problem(rows[0])
            else:
                # Clear window because of empty list of problems!
                self._set_problem(None)

    @handle_problem_and_source_errors
    def on_gac_delete_activate(self, action, parameter):
        for prblm in self._get_selected(self.lss_problems):
            try:
                self._controller.delete(prblm)
            except errors.InvalidProblem as ex:
                logging.debug(traceback.format_exc())
                self._remove_problem_from_storage(ex.problem_id)

    @handle_problem_and_source_errors
    def on_gac_detail_activate(self, action, parameter):
        selected = self._get_selected(self.lss_problems)
        if selected:
            wrappers.show_problem_details_for_dir(
                    selected[0].problem_id, self)

    @handle_problem_and_source_errors
    def on_gac_report_activate(self, action, parameter):
        selected = self._get_selected(self.lss_problems)
        if selected and not selected[0]['not-reportable']:
            # For gnome-shell to associate the child process windows with this application.
            os.environ["LIBREPORT_PRGNAME"] = self.get_application().get_application_id()
            self._controller.report(selected[0])

    @Gtk.Template.Callback()
    @handle_problem_and_source_errors
    def on_se_problems_search_changed(self, entry):
        self._filter.set_pattern(entry.get_text())

    def _on_key_press_event(self, sender, event):
        handled = self.search_entry.handle_event(event)
        if handled:
            bounds = self.search_entry.get_selection_bounds()
            if not bounds:
                position = self.search_entry.get_position()
                bounds = (position, position)
            self.search_entry.grab_focus()
            self.search_entry.select_region(bounds[0], bounds[1])
        return handled

    def on_gac_search_activate(self, action, parameter):
        self.search_entry.grab_focus()

    def on_gac_control_preferences_activate(self, action):
        wrappers.show_events_list_dialog(self)

    def on_gac_open_directory_activate(self, action, parameter):
        selection = self._get_selected(self.lss_problems)
        if selection:
            if os.path.exists(selection[0].problem_id):
                Gio.app_info_launch_default_for_uri(
                                    'file://' + selection[0].problem_id, None)
        self.menu_problem_item.popdown()
        self.menu_multiple_problems.popdown()

    def on_gac_copy_id_activate(self, action, parameter):
        selection = self._get_selected(self.lss_problems)
        if selection:
            #pylint: disable=E1101
            if os.path.exists(selection[0].problem_id):
                (Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                    .set_text(selection[0].problem_id, -1))
        self.menu_problem_item.popdown()
        self.menu_multiple_problems.popdown()

    @Gtk.Template.Callback()
    def problems_button_press_event(self, sender, data):
        # getattribute() used because number as first character in name
        # is syntax error
        if (data.type == type.__getattribute__(Gdk.EventType, '2BUTTON_PRESS')
                and data.button == Gdk.BUTTON_PRIMARY):
            action = self.lookup_action('report')
            action.activate()
        elif (data.type == Gdk.EventType.BUTTON_PRESS
                and data.button == Gdk.BUTTON_SECONDARY):
            if len(self.lss_problems.get_selected_rows()) > 1:
                self.menu_multiple_problems.popup_at_pointer(data)
                return True
            else:
                problem_row = self.lb_problems.get_row_at_y(data.y)
                if problem_row:
                    self.lb_problems.select_row(problem_row)
                    self.menu_problem_item.popup_at_pointer(data)
        return None

    def get_box_header_left_offset(self):
        # Returns the offset of box_header_left relative to the main paned
        # widget: distance between the left edges of the widgets in LTR
        # locales or the right edges in RTL locales.
        box_header_left = self.box_header_left
        box_panel_left = self.box_panel_left
        paned = box_panel_left.get_parent()
        if paned is None:
            # Fatal error, we can't do anything so just return error.
            # See also: rhbz#1347951
            return None

        offset = box_header_left.translate_coordinates(paned, 0, 0)[0]
        # We don't know who is the parent of box_header_left, it may be
        # box_header or header_bar.
        parent = box_header_left.get_parent()
        if parent is not None:
            if parent.get_direction() == Gtk.TextDirection.RTL:
                offset = paned.get_allocation().width - offset - \
                         box_header_left.get_allocation().width

        return offset

    def do_box_header_left_size_allocate(self, sender):
        # When something changes in the left group of header widgets
        # (for example the number of "My" or "System" bugs is changed
        # and requires more or less space) get its new minimum width
        # and set it as the minimum width of the left panel.
        # Unfortunately, we can't just call sender.get_preferred_width()
        # because once we set the minimum width (set_size_request())
        # of this box that value may be returned rather than the real
        # minimum value required by the box. So here we repeat roughly
        # the same algorithm which is inside the GtkBox implementation:
        # calculate the sum of minimum widths required by the children.
        spacing = sender.get_spacing()
        sum_width = -spacing
        for child in sender.get_children():
            width = child.get_preferred_width()[0]  # child's minimum width
            sum_width += width
            sum_width += spacing

        # Calculate the position of the box relative to its parent
        offset = self.get_box_header_left_offset()
        if offset is None:
            return GLib.SOURCE_REMOVE  # Error, we won't retry

        context = self.box_header_left.get_style_context()
        state = context.get_state()
        padding = context.get_padding(state)
        minimum_width = sum_width + offset + \
                        padding.right + padding.left

        self.box_panel_left.set_size_request(minimum_width, -1)

        return GLib.SOURCE_REMOVE

    @Gtk.Template.Callback()
    def on_box_header_left_size_allocate(self, sender, allocation):
        other = self.box_panel_left

        # Sometimes this function is called too early. All widgets must
        # be realized in order to measure their relative position.
        if not sender.get_realized() or not other.get_realized():
            return

        # We can't set the new size request while a widget size is being
        # allocated because the widget must be fully measured and the new
        # size request clears the measured flag causing a warning. For the
        # same reason we can't set the new size request of another widget
        # sharing the same common toplevel because the new size requsest
        # causes resize of all its parents including the common parent which
        # is just being allocated. To avoid this we schedule this action
        # on idle.
        GLib.idle_add(self.do_box_header_left_size_allocate, sender)

    def update_box_header_left_size_from_paned(self, sender):
        # Sets the box_header_left width the same as the paned position
        # minus optional margins
        other = self.box_header_left

        # Sometimes this function is called too early. All widgets must
        # be realized in order to measure their relative position.
        if not sender.get_realized() or not other.get_realized():
            return GLib.SOURCE_REMOVE

        offset = self.get_box_header_left_offset()
        if offset is None:
            return GLib.SOURCE_REMOVE  # Error, we won't retry

        self.box_header_left.set_size_request(
                sender.get_position() - offset, -1)

        # Sometimes the new width request is accepted (get_size_request()
        # returns the new value correctly) but not applied (the actual widget
        # width is old and unnecessarily larger). Not sure whose bug this is
        # but to workaround let's force resize.
        self.box_header_left.queue_resize()
        return GLib.SOURCE_REMOVE

    @Gtk.Template.Callback()
    def on_paned_position_changed(self, sender, data):
        # Alternatively we could watch box_panel_left size-allocate signal
        # but that other method seemed to be delayed and not updated the
        # size correctly.
        self.update_box_header_left_size_from_paned(sender)

    @Gtk.Template.Callback()
    def on_paned_size_allocate(self, sender, allocation):
        # Sometimes when the paned position is changed as a result of the
        # resize of whole window (for example unmaximization) the paned
        # position is not notified correctly. Again, not sure whose bug this
        # is but to workaround let's watch the size of the paned and update
        # the header box size. Same as previously, we should not resize
        # any widget even when another widget is being allocated so schedule
        # this action on idle.
        GLib.idle_add(self.update_box_header_left_size_from_paned, sender)

    @Gtk.Template.Callback()
    def on_paned_map(self, sender):
        # Also on the first appearance force the paned position changed event
        # to update the box_header_left minimum width. Otherwise it is not
        # adjusted to the paned handle position until a user moves the handle
        # manually.
        self.on_paned_position_changed(sender, None)
