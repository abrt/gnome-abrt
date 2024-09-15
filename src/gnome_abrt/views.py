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
import gi

#pylint: disable=E0611
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Adw
#pylint: disable=E0611
from gi.repository import Gdk
#pylint: disable=E0611
from gi.repository import Gio
#pylint: disable=E0611
from gi.repository import Pango
#pylint: disable=E0611
from gi.repository import GLib
import humanize

from gi.repository import GObject

from gnome_abrt import problems, config, wrappers, errors
from gnome_abrt.l10n import _, C_, GETTEXT_PROGNAME

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
                logging.debug("Problem '%s' doesn't have '%s'", problem.problem_id, i)
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
                rid = rid.rstrip('/').rsplit('/', maxsplit=1)[-1]
                rid = rid.rsplit('=', maxsplit=1)[-1]
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

    return (name,
            humanize.naturaltime(datetime.datetime.now()-problem['date_last']),
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

        
        #applying margins directly on the ListBoxRow
        self.set_margin_top(5)
        self.set_margin_bottom(5)
        self.set_margin_start(5)
        self.set_margin_end(5)

        grid = Gtk.Grid.new()
        grid.set_column_spacing(12)

        self.set_child(grid)

        self._lbl_app = Gtk.Label.new(problem_values[0])
        self._lbl_app.set_halign(Gtk.Align.START)
        self._lbl_app.set_hexpand(True)
        #self._lbl_app.set_alignment(0.0, 0.5)
        self._lbl_app.set_xalign(0.0)
        self._lbl_app.set_yalign(0.5)
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
        #self._lbl_type.set_alignment(0.0, 0.5)
        self._lbl_type.set_xalign(0.0)
        self._lbl_type.set_yalign(0.5)
        self._lbl_type.get_style_context().add_class('dim-label')

        grid.attach_next_to(self._lbl_type, self._lbl_app, Gtk.PositionType.BOTTOM, 1, 1)

        self._lbl_count = Gtk.Label.new(problem_values[3])
        self._lbl_count.set_halign(Gtk.Align.END)
        self._lbl_count.get_style_context().add_class('times-detected-label')
        #showing lbl_count if the count is greater than 1
        if int(problem_values[3]) > 1:
            self._lbl_count.show()
        else:
            self._lbl_count.hide()

        grid.attach_next_to(self._lbl_count, self._lbl_type, Gtk.PositionType.RIGHT, 1, 1)

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
    box_panel_left = Gtk.Template.Child()
    detected_crashes_label = Gtk.Template.Child()
    crash_box = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    btn_search_icon = Gtk.Template.Child()
    lbl_reason = Gtk.Template.Child()
    lbl_summary = Gtk.Template.Child()
    lbl_type_crash = Gtk.Template.Child()
    lbl_app_name_value = Gtk.Template.Child()
    lbl_app_version_value = Gtk.Template.Child()
    lbl_detected_value = Gtk.Template.Child()
    lbl_reported = Gtk.Template.Child()
    lbl_reported_value = Gtk.Template.Child()
    lbl_times_detected_value = Gtk.Template.Child()
    lb_problems = Gtk.Template.Child()
    nb_problem_layout = Gtk.Template.Child()
    btn_delete = Gtk.Template.Child()
    btn_report = Gtk.Template.Child()
    app_menu_button = Gtk.Template.Child()
    vbx_links = Gtk.Template.Child()
    vbx_problem_messages = Gtk.Template.Child()
    gd_problem_info = Gtk.Template.Child()
    vbx_empty_page = Gtk.Template.Child()
    gr_main_layout = Gtk.Template.Child()

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

        builder = Gtk.Builder()
        builder.set_translation_domain(GETTEXT_PROGNAME)
        builder.add_from_resource('/org/freedesktop/GnomeAbrt/ui/oops-menus.ui')

        self.app_menu_button.set_menu_model(builder.get_object('app_menu'))

        self.menu_problem_item = builder.get_object('menu_problem_item')
        #self.menu_problem_item = Gtk.Menu.new_from_model(self.menu_problem_item)
        self.menu_problem_item = Gtk.PopoverMenu.new_from_model(self.menu_problem_item) #jft

        #self.menu_problem_item.attach_to_widget(self) #jft

        self.menu_multiple_problems = builder.get_object(
                'menu_multiple_problems')
        #self.menu_multiple_problems = Gtk.Menu.new_from_model(
        #        self.menu_multiple_problems)
        self.menu_multiple_problems = Gtk.PopoverMenu.new_from_model(self.menu_multiple_problems) #jft

        #self.menu_multiple_problems.attach_to_widget(self) #jft

        #pylint: disable=E1120
        css_prv = Gtk.CssProvider.new()
        css_prv.load_from_resource('/org/freedesktop/GnomeAbrt/css/oops.css')
        stl_ctx = self.get_style_context()
        #stl_ctx.add_provider_for_screen(stl_ctx.get_screen(), css_prv, 6000)
        #stl_ctx.add_provider_for_display(Gdk.Display.get_default(), css_prv, 6000) #jft
        stl_ctx.add_provider_for_display(Gdk.Display.get_default(), css_prv,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_USER)

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

        self._add_actions(application)

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

        #self.lb_problems.connect("key-press-event", self._on_key_press_event)
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_press_event)
        self.add_controller(key_controller)

        self.style_manager = Adw.StyleManager.get_default()
        self.update_theme()
        self.style_manager.connect("notify::color-scheme", self.on_theme_changed)

        self.search_entry.hide()  # Ensure the search entry is hidden on load

        # Ensure buttons are packed only once
        if self.btn_delete.get_parent() is None:
            self.header_bar.pack_end(self.btn_delete)
        if self.btn_report.get_parent() is None:
            self.header_bar.pack_end(self.btn_report)
        if self.app_menu_button.get_parent() is None:
            self.header_bar.pack_end(self.app_menu_button)
        self.box_header_left.set_hexpand(True)

        self.box_header_left.connect("notify::allocation", self.on_box_header_left_size_allocate)
        self.gr_main_layout.connect("notify::position", self.on_paned_position_changed)
        self.gr_main_layout.connect("notify::allocation", self.on_paned_size_allocate)
        self.btn_search_icon.connect('clicked', self.on_search_icon_clicked)
        self.search_entry.connect('notify::text', self.on_search_entry_text_changed)
        self.search_entry.connect('search-changed', self.on_se_problems_search_changed)
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", self.problems_button_press_event)
        self.lb_problems.add_controller(gesture)
        self.lbl_reason.get_style_context().add_class('oops-reason')
        self.detected_crashes_label.get_style_context().add_class('app-name-label')
        self.crash_box.get_style_context().add_class('crash-info-box')

        #"map" event is emitted when the window is initialized
        self.connect("map", self.on_window_map)

    #box_header_left and box_panel_left were not properly aligned or sized the same way on window initialization.
    #This was likely because the GTK layout system sometimes doesn't properly propagate the size allocation across all widgets immediately on startup
    #Even though both panels are inside a GtkPaned, the initial size calculation didn't seem to synchronize their widths correctly
    #as a result, the box_header_left width remained smaller than box_panel_left.
    #did this to solve the issue: Force Layout Recalculation by Adjusting the Pane and slight Separator Shift
    def on_window_map(self, widget):
        """This function triggers when the window is first shown"""
        #after the window is initialized, adjust the paned position slightly to the right
        current_position = self.gr_main_layout.get_position()
        #slightly move the separator of the paned (move it 10 pixels to the right)
        self.gr_main_layout.set_position(current_position + 10)
        #move it back to the original position after a slight delay
        GLib.idle_add(self.restore_paned_position, current_position)

    def restore_paned_position(self, original_position):
        """Optional: restoring the original paned position after the adjustment - might delete later"""
        self.gr_main_layout.set_position(original_position)
        return False  #returning False to remove the idle callback after execution

    def on_theme_changed(self, style_manager, _):
        """Handle theme changes."""
        self.update_theme()

    def update_theme(self):
        """Update the application theme based on system preference."""
        if self.style_manager.get_color_scheme() == Adw.ColorScheme.FORCE_DARK:
            logging.debug("Dark theme activated")
        elif self.style_manager.get_color_scheme() == Adw.ColorScheme.FORCE_LIGHT:
            logging.debug("Light theme activated")
        else:
            logging.debug("System theme activated")


    def _add_actions(self, application):
        action_entries = [
            ('delete', self.on_gac_delete_activate,),
            ('report', self.on_gac_report_activate,),
            ('open-directory', self.on_gac_open_directory_activate,),
            ('copy-id', self.on_gac_copy_id_activate,),
            ('search', self.on_gac_search_activate,),
        ]

        self.add_action_entries(action_entries)

        application.set_accels_for_action('win.delete', ['Delete'])
        application.set_accels_for_action('win.report', ['Return'])
        application.set_accels_for_action('win.open-directory', ['<Primary>o'])
        application.set_accels_for_action('win.copy-id', ['<Primary>c'])
        application.set_accels_for_action('win.search', ['<Primary>f'])

    def _configure_sources(self, sources):
        stack = Gtk.Stack()
        for name, src in sources:
            self._all_sources.append(src)
            src.attach(self._source_observer)

            label = None
            try:
                label = format_button_source_name(name, src)
            except errors.UnavailableSource:
                logging.debug("Unavailable source: %s", name)
                continue

            src.name = name
            src.button = None

        self._source = self._all_sources[0]

    def _update_source_button(self, source):
        name = format_button_source_name(source.name, source)

    def _set_button_toggled(self, button, state):
        pass

    def _on_source_btn_clicked(self, btn, args):
        pass

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
                self._all_sources.pop(source_index)

        if source != self._source:
            return
        
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
            logging.debug("Exception: %s", traceback.format_exc())
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

        #completely removing the row from the list
        self.lb_problems.remove(problem_row)
        problem_row.unparent()  #safely removing the row without destroying it

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
                logging.debug("Exception: %s", traceback.format_exc())
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
                    logging.debug("Exception: %s", traceback.format_exc())

        old_selection = self._get_selected(self.lss_problems)

        self._reloading = True
        try:
            #self.lb_problems.foreach(lambda w, u: w.destroy(), None)
            #jft
            child = self.lb_problems.get_first_child()
            while child:
                next_child = child.get_next_sibling()
                self.lb_problems.remove(child)
                child = next_child

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
            logging.debug("Can't select problem id '%s' because the id was not found", problem_id)

    def _show_problem_links(self, submissions):
        if not submissions:
            return False

        link_added = False
        for sbm in submissions:
            if problems.Problem.Submission.URL == sbm.rtype:
                title_escaped = GLib.markup_escape_text(sbm.title)
                lnk = Gtk.Label.new(sbm.title)
                lnk.set_use_markup(True)
                lnk.set_markup(f"<a href=\"{sbm.data}\">{title_escaped}</a>")
                lnk.set_halign(Gtk.Align.START)
                lnk.set_wrap(True)
                lnk.set_visible(True)
                self.vbx_links.append(lnk) #jft
                link_added = True

        return link_added

    def _show_problem_message(self, message):
        msg = Gtk.Label.new(message)
        msg.set_markup(message)
        msg.set_visible(True)
        msg.set_halign(Gtk.Align.START)
        msg.set_valign(Gtk.Align.START)
        msg.set_wrap(True)
        msg.set_selectable(True)
        msg.set_xalign(0)
        self.vbx_problem_messages.append(msg) #jft

    def _get_reason_for_problem_type(self, application, problem_type, human_type):
        if problem_type == 'Kerneloops':
            return _("Unexpected system error")
        if problem_type == 'vmcore':
            return _("Fatal system failure")

        if application.name:
            return _("{0} quit unexpectedly").format(application.name)

        # Translators: If application name is unknown,
        # display neutral header "'Type' problem has been detected".
        # Examples:
        #  Kerneloops problem has been detected
        #  C/C++ problem has been detected
        #  Python problem has been detected
        #  Ruby problem has been detected
        #  VMCore problem has been detected
        #  AVC problem has been detected
        #  Java problem has been detected
        return _("{0} problem has been detected").format(human_type)

    def _get_summary_for_problem_type(self, problem_type):
        if problem_type == 'Kerneloops':
            return _("The system has encountered a problem and recovered.")
        if problem_type == 'vmcore':
            return _("The system has encountered a problem and could not continue.")

        return _("The application encountered a problem and could not continue.")

    @handle_problem_and_source_errors
    def _set_problem(self, problem):
        def destroy_links(widget):
            if widget != self.lbl_reported_value:
                widget.unparent()

        self.selected_problem = problem

        action_enabled = problem is not None

        self.lookup_action('delete').set_enabled(action_enabled)
        self.lookup_action('report').set_enabled(action_enabled and not problem['not-reportable'])

        # Iterate through children and destroy them
        child = self.vbx_links.get_first_child()
        while child:
            destroy_links(child)
            child = child.get_next_sibling()

        child = self.vbx_problem_messages.get_first_child()
        while child:
            child.unparent()
            child = child.get_next_sibling()


        #if not problem:
        #    self.nb_problem_layout.set_visible_child(self.vbx_empty_page if self._source else self.vbx_no_source_page)

        #    return
        
        self.nb_problem_layout.set_visible_child(self.gd_problem_info)

        app = problem['application']

        #lbl_type_crash
        # I'm ensuring that before applying a new crash class,
        # the old ones (application-crash, system-crash, system-failure) are removed to avoid incorrect styling
        style_context = self.crash_box.get_style_context()
        style_context.remove_class('application-crash')
        style_context.remove_class('system-crash')
        style_context.remove_class('system-failure')
        
        problem_type_crash = problem['type']
        if problem_type_crash == "CCpp":
            # Translators: These are the problem types displayed in the problem
            # list under the application name
            problem_type_crash = _("Application Crash")
            self.crash_box.get_style_context().add_class('application-crash')
        elif problem_type_crash == "vmcore":
            problem_type_crash = _("System Crash")
            self.crash_box.get_style_context().add_class('system-crash')
        elif problem_type_crash == "Kerneloops":
            problem_type_crash = _("System Failure")
            self.crash_box.get_style_context().add_class('system-failure')
        else:
            problem_type_crash = _("Misbehavior")
            self.crash_box.get_style_context().add_class('application-crash')
        self.lbl_type_crash.set_text(problem_type_crash)

        self.lbl_reason.set_text(self._get_reason_for_problem_type(app, problem['type'], problem['human_type']))
        self.lbl_summary.set_text(self._get_summary_for_problem_type(problem['type']))

        # Translators: package name not available
        self.lbl_app_name_value.set_text(problem['package_name'] or _("N/A"))
        # Translators: package version not available
        self.lbl_app_version_value.set_text(problem['package_version'] or _("N/A"))
        self.lbl_detected_value.set_text(humanize.naturaltime(datetime.datetime.now()-problem['date']))
        self.lbl_detected_value.set_tooltip_text(problem['date'].strftime(config.get_configuration()['D_T_FMT']))

        self.lbl_times_detected_value.set_text(str(problem['count']))

        self.lbl_reported_value.show()
        self.lbl_reported.set_text(_("Reported"))
        if problem['not-reportable']:
            self.lbl_reported_value.set_text(_('cannot be reported'))

            self._show_problem_links(problem['submission'])
            self._show_problem_message(problem['not-reportable'])
        elif problem['is_reported']:
            if self._show_problem_links(problem['submission']):
                self.lbl_reported.set_text(_("Reports"))
                self.lbl_reported_value.hide()

                if not any((s.name == "Bugzilla" for s in problem['submission'])):
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

    def _get_selected(self, selection):
        return selection.get_selected_rows()
    
            
    def on_tvs_problems_changed(self, selection):
        if not self._reloading:
            rows = self._get_selected(selection)
            if rows:
                self._set_problem(rows[0])
            else:
                # Clear window because of empty list of problems!
                self._set_problem(None)

    
    @handle_problem_and_source_errors
    def on_gac_delete_activate(self, action, parameter, user_data):
        # Get the selected row (single selection)
        selected = self._get_selected(self.lss_problems)
        
        if selected:
            try:
                # Delete the selected problem
                self._controller.delete(selected[0])
                # Find the corresponding row and remove it from the list
                problem_row = self._find_problem_row(selected[0])
                if problem_row:
                    self.lb_problems.remove(problem_row)
            except errors.InvalidProblem as ex:
                logging.debug(traceback.format_exc())
                self._remove_problem_from_storage(ex.problem_id)


    @handle_problem_and_source_errors
    def on_gac_report_activate(self, action, parameter, user_data):
        selected = self._get_selected(self.lss_problems)
        if selected and not selected[0]['not-reportable']:
            # For gnome-shell to associate the child process windows with this application.
            os.environ["LIBREPORT_PRGNAME"] = self.get_application().get_application_id()
            self._controller.report(selected[0])
    
    
    def on_search_entry_text_changed(self, search_entry, gparam):
        """Hides the search entry when it is cleared (cross button clicked)."""
        if not search_entry.get_text():
            search_entry.hide()  # Hide the search entry if the text is empty

    def on_search_icon_clicked(self, button):
        logging.debug("search icon clicked");
        if self.search_entry.get_visible():
            logging.debug("hiding search entry")
            self.search_entry.hide()
        else:
            logging.debug("showing search entry")
            self.search_entry.show()
            self.search_entry.grab_focus()

    @handle_problem_and_source_errors
    def on_se_problems_search_changed(self, entry):
        self._filter.set_pattern(entry.get_text())

    
    def _on_key_press_event(self, controller, keyval, keycode, state):
        if self.search_entry.get_visible() and self.search_entry.has_focus():
            self.search_entry.emit_stop_by_name("key-pressed")
            bounds = self.search_entry.get_selection_bounds()
            if not bounds:
                position = self.search_entry.get_position()
                bounds = (position, position)
            self.search_entry.grab_focus()
            self.search_entry.select_region(bounds[0], bounds[1])
            return True
        return False
    

    def on_gac_search_activate(self, action, parameter, user_data):
        self.search_entry.grab_focus()

    def on_gac_open_directory_activate(self, action, parameter, user_data):
        selection = self._get_selected(self.lss_problems)
        if selection:
            if os.path.exists(selection[0].problem_id):
                Gio.app_info_launch_default_for_uri(
                                    'file://' + selection[0].problem_id, None)
        self.menu_problem_item.popdown()
        self.menu_multiple_problems.popdown()

    
    def on_gac_copy_id_activate(self, action, parameter, user_data):
        selection = self._get_selected(self.lss_problems)
        if selection:
            problem_id = selection[0].problem_id
            clipboard = Gdk.Display.get_default().get_clipboard()
            value = GObject.Value()
            value.init(GObject.TYPE_STRING)
            value.set_string(problem_id)
            content_provider = Gdk.ContentProvider.new_for_value(value)
            clipboard.set_content(content_provider)
        self.menu_problem_item.popdown()
        self.menu_multiple_problems.popdown()

    
    def problems_button_press_event(self, gesture, n_press, x, y):
        # Determine the type of click based on the number of presses
        if n_press == 2:  # Double click
            action = self.lookup_action('report')
            action.activate()
        elif n_press == 1:  # Single click
            button = gesture.get_current_button()
            if button == Gdk.BUTTON_SECONDARY:
                if len(self.lss_problems.get_selected_rows()) > 1:
                    self.menu_multiple_problems.set_parent(self)
                    self.menu_multiple_problems.popup_at_pointer(None)
                    return True
                problem_row = self.lb_problems.get_row_at_y(y)
                if problem_row:
                    self.lb_problems.select_row(problem_row)
                    self.menu_problem_item.set_parent(self)
                    self.menu_problem_item.popup_at_pointer(None)
        return None
        
    def get_box_header_left_offset(self):
        box_header_left = self.box_header_left
        box_panel_left = self.box_panel_left
        paned = box_panel_left.get_parent()
        if paned is None:
            return None

        offset = box_header_left.translate_coordinates(paned, 0, 0)[0]
        parent = box_header_left.get_parent()
        if parent is not None:
            if parent.get_direction() == Gtk.TextDirection.RTL:
                offset = paned.get_allocation().width - offset - \
                         box_header_left.get_allocation().width

        return offset

    def do_box_header_left_size_allocate(self, sender):
        spacing = sender.get_spacing()
        sum_width = -spacing
        for child in sender.get_children():
            width = child.get_preferred_width()[0]
            sum_width += width
            sum_width += spacing

        
        offset = self.get_box_header_left_offset()
        if offset is None:
            return GLib.SOURCE_REMOVE

        context = self.box_header_left.get_style_context()
        state = context.get_state()
        padding = context.get_padding(state)
        minimum_width = sum_width + offset + \
                        padding.right + padding.left

        self.box_panel_left.set_size_request(minimum_width, -1)

        return GLib.SOURCE_REMOVE


    
    def on_box_header_left_size_allocate(self, sender, allocation):
        other = self.box_panel_left
        if not sender.get_realized() or not other.get_realized():
            return
        GLib.idle_add(self.do_box_header_left_size_allocate, sender)

    def update_box_header_left_size_from_paned(self, sender):
        other = self.box_header_left

        if not sender.get_realized() or not other.get_realized():
            return GLib.SOURCE_REMOVE

        offset = self.get_box_header_left_offset()
        if offset is None:
            return GLib.SOURCE_REMOVE
        
        width = max(sender.get_position() - offset, 0)
        self.box_header_left.set_size_request(width, -1)

        
        self.box_header_left.queue_resize()
        return GLib.SOURCE_REMOVE
    
    
    def on_paned_position_changed(self, sender, data):
        #temporarily disable resizing of the main window during pane adjustment
        self.set_resizable(False)

        #a minimum width for the left pane (box_panel_left)
        min_left_width = 280

        #maximum width of left pane
        max_left_width = 600

        #current position of the pane
        current_position = sender.get_position()

        #box_panel_left)is not resized smaller than the minimum width
        if current_position < min_left_width:
            sender.set_position(min_left_width)
        elif current_position > max_left_width:
            sender.set_position(max_left_width)

        self.update_box_header_left_size_from_paned(sender)

        #enable window resizing after the adjustment is complete
        self.set_resizable(True)

    
    
    def on_paned_size_allocate(self, sender, allocation):
        GLib.idle_add(self.update_box_header_left_size_from_paned, sender)
    

    
    def on_paned_map(self, sender):
        self.on_paned_position_changed(sender, None)
