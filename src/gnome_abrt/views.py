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
import humanize
import datetime

#pygobject
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

import gnome_abrt.problems as problems
import gnome_abrt.config as config
import gnome_abrt.wrappers as wrappers
import gnome_abrt.errors as errors
import gnome_abrt.desktop as desktop
from gnome_abrt import GNOME_ABRT_UI_DIR
from gnome_abrt.tools import fancydate, smart_truncate, load_icon
from gnome_abrt.tools import set_icon_from_pixbuf_with_scale
from gnome_abrt.l10n import _, GETTEXT_PROGNAME


def list_box_row_to_problem(list_box_row):
    return list_box_row.get_children()[0].get_problem()


def list_box_row_set_values(list_box_row, values):
    return list_box_row.get_children()[0].set_values(values)


class ProblemsFilter(object):

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

        problem = list_box_row_to_problem(list_box_row)

        for i in ['component', 'reason', 'executable', 'package']:
            if problem[i] is None:
                logging.debug("Problem '{0}' doesn't have '{1}"
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

    if name == "kernel":
        name = _("System")

    return (smart_truncate(name, length=40),
            fancydate(problem['date_last']),
            problem['count'],
            problem)


#pylint: disable=W0613
def time_sort_func(first_row, second_row, trash):
    fst_problem = list_box_row_to_problem(first_row)
    scn_problem = list_box_row_to_problem(second_row)
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


class ListBoxSelection(object):

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
        return [list_box_row_to_problem(lbr)
                for lbr in self._lb.get_selected_rows()]


class ProblemListBoxCell(Gtk.Box):

    def __init__(self, problem_values):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL,
                spacing=0, homogeneous=False)

        self.get_style_context().add_class('problem-cell')

        self._problem = problem_values[3]

        self._hbox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 12)

        self._lbl_app = Gtk.Label.new(problem_values[0])
        self._lbl_app.set_halign(Gtk.Align.START)
        self._lbl_app.set_alignment(0.0, 0.5)
        self._lbl_app.set_ellipsize(Pango.EllipsizeMode.END)
        self._lbl_app.set_width_chars(15)
        self._lbl_app.get_style_context().add_class('app-name-label')

        self._lbl_date = Gtk.Label.new(problem_values[1])
        self._lbl_date.set_halign(Gtk.Align.END)
        self._lbl_date.get_style_context().add_class('dim-label')

        self._lbl_count = Gtk.Label.new(problem_values[2])
        self._lbl_count.set_halign(Gtk.Align.END)
        self._lbl_count.get_style_context().add_class('dim-label')

        self._hbox.pack_start(self._lbl_app, False, True, 0)
        self._hbox.pack_end(self._lbl_date, False, True, 0)

        self.pack_start(self._hbox, True, True, 0)
        self.pack_start(self._lbl_count, True, True, 0)
        self.show_all()

    def set_values(self, problem_values):
        self._lbl_app.set_text(problem_values[0])
        self._lbl_date.set_text(problem_values[1])
        self._lbl_count.set_text(problem_values[2])
        self._problem = problem_values[3]

    def get_problem(self):
        return self._problem


#pylint: disable=R0902
class OopsWindow(Gtk.ApplicationWindow):

    _TITLE = _("Problem Reporting")

    class OopsGtkBuilder(object):
        def __init__(self):
            builder = None
            # try to load the glade from git at first step
            ui_files = ['./src/gnome_abrt/oops.glade',
                        GNOME_ABRT_UI_DIR + '/oops.glade']
            for glade_file in ui_files:
                if os.path.exists(glade_file):
                    builder = Gtk.Builder()
                    builder.set_translation_domain(GETTEXT_PROGNAME)
                    try:
                        builder.add_from_file(filename=glade_file)
                    #pylint: disable=E0712
                    except GObject.GError as ex:
                        builder = None
                        logging.debug("Failed to load UI file: '{0}': {1}"
                                .format(glade_file, str(ex)))
                    else:
                        break
                else:
                    logging.debug("UI file does not exist: '{0}'"
                            .format(glade_file))

            if builder is None:
                raise RuntimeError(_("Failed to load UI definition"))

            self._builder = builder

            self.wnd_main = builder.get_object('wnd_main')
            self.box_window = builder.get_object('box_window')
            self.box_sources_switcher = builder.get_object(
                    'box_sources_switcher')
            self.lbl_reason = builder.get_object('lbl_reason')
            self.lbl_summary = builder.get_object('lbl_summary')
            self.lbl_app_name_value = builder.get_object('lbl_app_name_value')
            self.lbl_app_version_value = builder.get_object(
                    'lbl_app_version_value')
            self.lbl_detected_value = builder.get_object('lbl_detected_value')
            self.lbl_reported = builder.get_object('lbl_reported')
            self.lbl_reported_value = builder.get_object('lbl_reported_value')
            self.lbl_repots = builder.get_object('lbl_reports')
            self.lb_problems = builder.get_object('lb_problems')
            self.img_app_icon = builder.get_object('img_app_icon')
            self.nb_problem_layout = builder.get_object('nb_problem_layout')
            self.btn_delete = builder.get_object('btn_delete')
            self.btn_report = builder.get_object('btn_report')
            self.btn_detail = builder.get_object('btn_detail')
            self.se_problems = builder.get_object('se_problems')
            self.search_bar = builder.get_object('search_bar')
            self.chb_all_problems = builder.get_object('chb_all_problems')
            self.vbx_links = builder.get_object('vbx_links')
            self.vbx_problem_messages = builder.get_object(
                    'vbx_problem_messages')
            self.gac_report = builder.get_object('gac_report')
            self.gac_delete = builder.get_object('gac_delete')
            self.gac_open_directory = builder.get_object('gac_open_directory')
            self.gac_copy_id = builder.get_object('gac_copy_id')
            self.gac_search = builder.get_object('gac_search')
            self.menu_problem_item = builder.get_object('menu_problem_item')
            self.menu_multiple_problems = builder.get_object(
                    'menu_multiple_problems')
            self.ag_accelerators = builder.get_object('ag_accelerators')
            self.header_bar = None

        def connect_signals(self, implementor):
            self._builder.connect_signals(implementor)

            self.search_bar.connect_entry(self.se_problems)

        def reset_window(self, window, title):
            window.set_default_size(*self.wnd_main.get_size())
            self.wnd_main.remove(self.box_window)
            #pylint: disable=E1101
            window.add(self.box_window)

            if desktop.replace_window_header():
                self.box_header.foreach(lambda w, c: c.remove(w),
                        self.box_header)

                self.header_bar = Gtk.HeaderBar.new()
                self.header_bar.pack_start(self.box_sources_switcher)
                self.header_bar.pack_start(self.tbtn_multi_select)
                self.header_bar.pack_end(self.btn_detail)
                self.header_bar.pack_end(self.btn_report)
                self.header_bar.pack_end(self.btn_delete)

                window.set_titlebar(self.header_bar)
                self.header_bar.set_show_close_button(True)
                # window.get_title() returns None
                self.header_bar.set_title(title)

            # move accelators group from the design window to this window
            window.add_accel_group(self.ag_accelerators)

        def __getattr__(self, name):
            obj = self._builder.get_object(name)

            if obj is None:
                raise AttributeError("Builder has not member '{0}'"
                        .format(name))

            return obj


    class SourceObserver(object):
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


    class OptionsObserver(object):
        def __init__(self, wnd):
            self.wnd = wnd

        def option_updated(self, conf, option):
            if option == 'problemid' and conf[option]:
                self.wnd._select_problem_by_id(conf[option])
            if option == 'T_FMT' and conf[option]:
                self.wnd._reload_problems(self.wnd._source)
            if option == 'D_T_FMT' and conf[option]:
                self.wnd._set_problem(self.wnd.selected_problem)


    def __init__(self, application, sources, controller):
        Gtk.ApplicationWindow.__init__(self,
                            title=OopsWindow._TITLE,
                            application=application)

        if not sources:
            raise ValueError("The source list cannot be empty!")

        self._builder = OopsWindow.OopsGtkBuilder()
        self._builder.reset_window(self, OopsWindow._TITLE)

        #pylint: disable=E1120
        css_prv = Gtk.CssProvider.new()
        css_prv.load_from_data("GtkListBoxRow {\n"
                               "  padding          : 12px;\n"
                               "}\n"
                               ".app-name-label {\n"
                               "  font-weight      : bold;\n"
                               "}\n"
                               ".oops-reason {\n"
                               "  font-size        : 120%;\n"
                               "  font-weight      : bold;\n"
                               "}\n".encode()
                               )
        stl_ctx = self.get_style_context()
        stl_ctx.add_provider_for_screen(stl_ctx.get_screen(), css_prv, 6000)
        self._builder.connect_signals(self)

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
        self._builder.lb_problems.set_sort_func(time_sort_func, self._trash)
        self.lss_problems = ListBoxSelection(self._builder.lb_problems,
                self.on_tvs_problems_changed)
        self._filter = ProblemsFilter(self._builder.lb_problems,
                self.lss_problems)

        self._builder.lb_problems.grab_focus()
        try:
            self._reload_problems(self._source)
        except errors.UnavailableSource as ex:
            self._disable_source(ex.source, ex.temporary)

        self._options_observer = OopsWindow.OptionsObserver(self)
        conf = config.get_configuration()
        conf.set_watch('problemid', self._options_observer)
        conf.set_watch('T_FMT', self._options_observer)
        conf.set_watch('D_T_FMT', self._options_observer)
        self._options_observer.option_updated(conf, 'problemid')
        self._builder.btn_detail.set_visible(conf['expert'])
        self._builder.mi_detail.set_visible(conf['expert'])

        # enable observer
        self._source_observer.enable()

        self.connect("key-press-event", self._on_key_press_event)


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
            self._builder.box_sources_switcher.pack_start(
                    src_btn, False, True, 0)

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
        lb_row = self._builder.lb_problems.get_row_at_index(i)
        while lb_row is not None:
            if problem == list_box_row_to_problem(lb_row):
                break

            i += 1
            lb_row = self._builder.lb_problems.get_row_at_index(i)

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
        problem_cell = ProblemListBoxCell(problem_values)
        self._builder.lb_problems.insert(problem_cell, -1)
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
                problem_row = self._builder.lb_problems.get_row_at_index(i)
                if self._filter.match(problem_row):
                    break

            if problem_row is not None:
                self._builder.lb_problems.select_row(problem_row)
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

            list_box_row_set_values(problem_row, values)
            self._builder.lb_problems.invalidate_sort()
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
            self._builder.lb_problems.foreach(
                lambda w, u: w.destroy(), None)

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
                problem_row = self._builder.lb_problems.get_row_at_index(i)
                i = 1

            while (problem_row is not None
                    and not self._filter.match(problem_row)):
                problem_row = self._builder.lb_problems.get_row_at_index(i)
                i += 1

            if problem_row is not None:
                self._builder.lb_problems.select_row(problem_row)
                return

        self._set_problem(None)

    def _select_problem_by_id(self, problem_id):
        # The problem could come from a different source than the currently
        # loaded source. If so, try to switch to problem's origin source and
        # select the problem after that.
        if (self._source is not None and
                not problem_id in self._source.get_problems()):
            for source in self._all_sources:
                if problem_id in source.get_problems():
                    res, old_source = self._switch_source(source)
                    if res:
                        self._set_button_toggled(old_source.button, False)
                        self._set_button_toggled(source.button, True)
                    break

        problem_row = self._find_problem_row(problem_id)

        if problem_row is not None:
            self._builder.lb_problems.select_row(problem_row)
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
                lnk.set_margin_top(5)
                lnk.set_margin_bottom(8)
                lnk.set_line_wrap(True)
                lnk.set_visible(True)

                self._builder.vbx_links.pack_start(lnk, False, True, 0)
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

        self._builder.vbx_problem_messages.pack_start(msg, False, True, 0)

    @handle_problem_and_source_errors
    def _set_problem(self, problem):
        def destroy_links(widget, _):
            if widget != self._builder.lbl_reported_value:
                widget.destroy()

        self.selected_problem = problem

        sensitive_btn = problem is not None
        self._builder.btn_delete.set_sensitive(sensitive_btn)
        self._builder.btn_report.set_sensitive(
                sensitive_btn and not problem['not-reportable'])
        self._builder.btn_detail.set_sensitive(sensitive_btn)
        self._builder.vbx_links.foreach(
                destroy_links, None)
        self._builder.vbx_problem_messages.foreach(
                lambda w, u: w.destroy(), None)

        if problem:
            self._builder.nb_problem_layout.set_current_page(0)
            app = problem['application']
            if problem['type'] == 'Kerneloops':
                self._builder.lbl_reason.set_text(
            _("Unexpected system error"))
                self._builder.lbl_summary.set_text(
            _("The system has encountered a problem and recovered."))
            elif problem['type'] == 'vmcore':
                self._builder.lbl_reason.set_text(
            _("Fatal system failure"))
                self._builder.lbl_summary.set_text(
            _("The system has encountered a problem and could not continue."))
            else:
                if not app.name:
                    # If Application's name is unknown, display neutral
                    # header "'Type' problem has been detected":
                    #  Kerneloops problem has been detected
                    #  C/C++ problem has been detected
                    #  Python problem has been detected
                    #  Ruby problem has been detected
                    #  VMCore problem has been detected
                    #  AVC problem has been detected
                    #  Java problem has been detected
                    self._builder.lbl_reason.set_text(
                            _("{0} problem has been detected").format(
                                    problem['human_type']))
                else:
                    self._builder.lbl_reason.set_text(
                            _("{0} quit unexpectedly").format(app.name))

                self._builder.lbl_summary.set_text(
            _("The application encountered a problem and could not continue."))

            self._builder.lbl_app_name_value.set_text(
                        problem['package_name'] or _("N/A"))
            self._builder.lbl_app_version_value.set_text(
                        problem['package_version'] or _("N/A"))
            self._builder.lbl_detected_value.set_text(
                humanize.naturaltime(datetime.datetime.now()-problem['date']))
            self._builder.lbl_detected_value.set_tooltip_text(
                problem['date'].strftime(config.get_configuration()['D_T_FMT']))

            icon_buf = None
            scale = self._builder.img_app_icon.get_scale_factor()
            if app.icon:
                icon_buf = load_icon(gicon=app.icon, scale=scale)

            if icon_buf is None:
                icon_buf = load_icon(name="system-run-symbolic", scale=scale)

            # icon_buf can be None and if it is None, no icon will be displayed
            set_icon_from_pixbuf_with_scale(self._builder.img_app_icon,
                                            icon_buf, scale)

            self._builder.lbl_reported_value.show()
            self._builder.lbl_reported.set_text(_("Reported"))
            if problem['not-reportable']:
                self._builder.lbl_reported_value.set_text(
                        _('cannot be reported'))
                self._show_problem_links(problem['submission'])
                self._show_problem_message(problem['not-reportable'])
            elif problem['is_reported']:
                if self._show_problem_links(problem['submission']):
                    self._builder.lbl_reported.set_text(_("Reports"))
                    self._builder.lbl_reported_value.hide()

                    if (not any((s.name == "Bugzilla"
                                for s in problem['submission']))):
                        self._show_problem_message(
_("This problem has been reported, but a <i>Bugzilla</i> ticket has not"
" been opened. Our developers may need more information to fix the problem.\n"
"Please consider also <b>reporting it</b> to Bugzilla in"
" order to provide that. Thank you."))
                else:
                    self._builder.lbl_reported_value.set_text(_('yes'))
            else:
                self._builder.lbl_reported_value.set_text(_('no'))
        else:
            if self._source is not None:
                self._builder.nb_problem_layout.set_current_page(1)
            else:
                self._builder.nb_problem_layout.set_current_page(2)

    def _get_selected(self, selection):
        return selection.get_selected_rows()

    def on_tbtn_multi_select_toggled(self, tbtn):
        if tbtn.get_active():
            self._builder.lb_problems.set_selection_mode(
                    Gtk.SelectionMode.MULTIPLE)
        else:
            row = self._builder.lb_problems.get_selected_row()
            if row is None:
                row = self._builder.lb_problems.get_row_at_index(0)

            self._builder.lb_problems.set_selection_mode(
                    Gtk.SelectionMode.BROWSE)

            if row is not None and self._filter.match(row):
                self._builder.lb_problems.select_row(row)

    def on_tvs_problems_changed(self, selection):
        if not self._reloading:
            rows = self._get_selected(selection)
            if rows:
                self._set_problem(rows[0])
            else:
                # Clear window because of empty list of problems!
                self._set_problem(None)

    @handle_problem_and_source_errors
    def on_gac_delete_activate(self, action):
        for prblm in self._get_selected(self.lss_problems):
            try:
                self._controller.delete(prblm)
            except errors.InvalidProblem as ex:
                logging.debug(traceback.format_exc())
                self._remove_problem_from_storage(ex.problem_id)

    @handle_problem_and_source_errors
    def on_gac_detail_activate(self, action):
        selected = self._get_selected(self.lss_problems)
        if selected:
            wrappers.show_problem_details_for_dir(
                    selected[0].problem_id, self)

    @handle_problem_and_source_errors
    def on_gac_analyze_activate(self, action):
        selected = self._get_selected(self.lss_problems)
        if selected:
            self._controller.analyze(selected[0])

    @handle_problem_and_source_errors
    def on_gac_report_activate(self, action):
        selected = self._get_selected(self.lss_problems)
        if selected and not selected[0]['not-reportable']:
            self._controller.report(selected[0])

    @handle_problem_and_source_errors
    def on_se_problems_search_changed(self, entry):
        self._filter.set_pattern(entry.get_text())

    def _on_key_press_event(self, sender, event):
        return self._builder.search_bar.handle_event(event)

    def _hide_problem_filter(self):
        self._builder.se_problems.set_text("")
        self._builder.search_bar.set_search_mode(False)

    def _show_problem_filter(self):
        self._builder.search_bar.set_search_mode(True)
        self._builder.se_problems.grab_focus()

    def on_se_problems_key_press_event(self, sender, data):
        if data.keyval == Gdk.KEY_Escape:
            self._hide_problem_filter()

        return False

    def on_gac_search_activate(self, action):
        if self._builder.search_bar.get_search_mode():
            self._hide_problem_filter()
        else:
            self._show_problem_filter()

    def on_gac_opt_all_problems_activate(self, action):
        conf = config.get_configuration()
        conf['all_problems'] = self._builder.chb_all_problems.get_active()

    def on_gac_control_preferences_activate(self, action):
        wrappers.show_events_list_dialog(self)

    def on_gac_open_directory_activate(self, action):
        selection = self._get_selected(self.lss_problems)
        if selection:
            Gio.app_info_launch_default_for_uri(
                                'file://' + selection[0].problem_id, None)
        self._builder.menu_problem_item.popdown()
        self._builder.menu_multiple_problems.popdown()

    def on_gac_copy_id_activate(self, action):
        selection = self._get_selected(self.lss_problems)
        if selection:
            #pylint: disable=E1101
            (Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                .set_text(selection[0].problem_id, -1))
        self._builder.menu_problem_item.popdown()
        self._builder.menu_multiple_problems.popdown()

    def problems_button_press_event(self, sender, data):
        # getattribute() used because number as first character in name
        # is syntax error
        if (data.type == type.__getattribute__(Gdk.EventType, '2BUTTON_PRESS')
                and data.button == Gdk.BUTTON_PRIMARY):
            self._builder.gac_report.activate()
        elif (data.type == Gdk.EventType.BUTTON_PRESS
                and data.button == Gdk.BUTTON_SECONDARY):
            if len(self.lss_problems.get_selected_rows()) > 1:
                self._builder.menu_multiple_problems.popup(None, None,
                        None, None, data.button, data.time)
                return True
            else:
                problem_row = self._builder.lb_problems.get_row_at_y(data.y)
                if problem_row:
                    self._builder.lb_problems.select_row(problem_row)
                    self._builder.menu_problem_item.popup(None, None,
                            None, None, data.button, data.time)
