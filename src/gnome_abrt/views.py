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
import traceback

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

        if item_match(pattern, problem) or pattern in problem.problem_id:
            return True

        app = problem['application']
        if app is None or app.name is None:
            return False

        return pattern in app.name

    pattern = data.current_pattern

    if len(pattern) == 0:
        return True

    return match_pattern(pattern, model[itrtr][2])


class ProblemsFilter(object):

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

    if app.name:
        name = app.name
        typ = problem['type']
    else:
        name = problem['type']
        typ = ""

    return ["{0!s}\n{1!s}".format(name, typ),
            "{0!s}\n{1!s}".format(fancydate(problem['date_last']),
                                  problem['count']),
            problem]

#pylint: disable=W0613
def time_sort_func(model, first, second, trash):
    # skip invalid problems which were marked invalid while sorting
    if (model[first][2].problem_id in trash or
        model[second][2].problem_id in trash):
        return 0

    try:
        lhs = model[first][2]['date_last'].timetuple()
        rhs = model[second][2]['date_last'].timetuple()
        return time.mktime(lhs) - time.mktime(rhs)
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


#pylint: disable=R0902
class OopsWindow(Gtk.ApplicationWindow):
    class OopsGtkBuilder(object):
        def __init__(self):
            builder = Gtk.Builder.new()
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
            self.lbl_reported = builder.get_object('lbl_reported')
            self.lbl_reported_value = builder.get_object('lbl_reported_value')
            self.lbl_repots = builder.get_object('lbl_reports')
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


    def __init__(self, application, sources, controller):
        Gtk.ApplicationWindow.__init__(self,
                            title=_('Automatic Bug Reporting Tool'),
                            application=application)

        if not sources:
            raise ValueError("The source list cannot be empty!")

        self._builder = OopsWindow.OopsGtkBuilder()
        self.set_default_size(*self._builder.wnd_main.get_size())
        self._builder.wnd_main.remove(self._builder.gr_main_layout)
        #pylint: disable=E1101
        self.add(self._builder.gr_main_layout)

        # move accelators group from the design window to this window
        self.add_accel_group(self._builder.ag_accelerators)

        css_prv = Gtk.CssProvider.new()
        css_prv.load_from_data("GtkViewport {\n"
                               "  background-color : @theme_bg_color;\n"
                               "}\n")
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
            self._builder.hbox_source_btns.pack_start(src_btn,
                    True, True, 0)

            # add an extra member name (I don't like it but it so easy)
            src.name = name
            # add an extra member button (I don't like it but it so easy)
            src.button = src_btn
            src_btn.connect("clicked", self._on_source_btn_clicked, src)

        self._source = self._all_sources[0]
        self._set_button_toggled(self._source.button, True)

        self._builder.ls_problems.set_sort_column_id(0, Gtk.SortType.DESCENDING)
        # a set where invalid problems found while sorting of the problem list
        # are stored
        self._trash = set()
        self._builder.ls_problems.set_sort_func(0, time_sort_func, self._trash)
        self._filter = ProblemsFilter(self, self._builder.tv_problems)

        self._builder.tv_problems.grab_focus()
        try:
            self._reload_problems(self._source)
        except errors.UnavailableSource as ex:
            self._disable_source(ex.source, ex.temporary)

        self._options_observer = OopsWindow.OptionsObserver(self)
        conf = config.get_configuration()
        conf.set_watch('problemid', self._options_observer)
        self._options_observer.option_updated(conf, 'problemid')
        self._builder.btn_detail.set_visible(conf['expert'])
        self._builder.mi_detail.set_visible(conf['expert'])

        # enable observer
        self._source_observer.enable()

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
    def _find_problem_iter(self, problem, model):
        pit = model.get_iter_first()
        while pit:
            if model[pit][2] == problem:
                return pit

            pit = model.iter_next(pit)

        return None

    def _add_problem_to_storage(self, problem):
        """Adds a problem to the storage

        Returns True if the problem was successfully added to the storage;
        otherwise returns False
        """
        problem_values = None
        try:
            problem_values = problem_to_storage_values(problem)
        except errors.InvalidProblem:
            logging.debug("Exception: {0}".format(traceback.format_exc()))
            return

        self._append_problem_values_to_storage(problem_values)

    def _append_problem_values_to_storage(self, problem_values):
        self._builder.ls_problems.append(problem_values)
        self._clear_invalid_problems_trash()

    def _clear_invalid_problems_trash(self):
        # GtkListStore.append()/set_value() methods trigger
        # time_sort_func() where InvalidProblem exception can occur. In that
        # case time_sort_func() pushes an invalid problem to the trash set
        # because the invalid problem cannot be removed while executing the
        # operation
        while self._trash:
            self._remove_problem_from_storage(self._trash.pop())

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
            except errors.InvalidProblem as ex:
                logging.debug("Exception: {0}".format(traceback.format_exc()))
                self._remove_problem_from_storage(ex.problem_id)
                return

            for i in xrange(0, len(values)-1):
                self._builder.ls_problems.set_value(pit, i, values[i])
                self._clear_invalid_problems_trash()

        if problem in self._get_selected(self._builder.tvs_problems):
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

        old_selection = self._get_selected(self._builder.tvs_problems)

        self._reloading = True
        try:
            self._builder.ls_problems.clear()

            if storage_problems:
                for p in storage_problems:
                    self._append_problem_values_to_storage(p)
        finally:
            self._reloading = False

        if storage_problems:
            model = self._builder.tv_problems.get_model()

            # For some strange reason, get_model() sometimes returns None when
            # this function is called from a signal handler but the signal
            # handler is synchronously called from GMainLoop so there is no
            # place for race conditions. If the described situation arises,
            # base model will be used.
            if model is None:
                model = self._builder.ls_problems

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
        if not submissions:
            return False

        link_added = False
        for sbm in submissions:
            if problems.Problem.Submission.URL == sbm.rtype:
                lnk = Gtk.LinkButton.new_with_label(sbm.data, sbm.title)
                lnk.set_visible(True)
                lnk.set_halign(Gtk.Align.START)
                lnk.set_valign(Gtk.Align.START)
                lnk_lbl = lnk.get_child()
                # using hasattr() because this constructions abuses a knowledge
                # of current Gtk.LinkButton implementation details, but there is
                # no other way how to make a text of Gtk.LinkButton wrapped
                # works fine with gtk-3.8.2 but in a future version of gtk, the
                # child will not necessarily be an instance of Gtk.Label
                if hasattr(lnk_lbl, "set_line_wrap"):
                    lnk_lbl.set_line_wrap(True)

                self._builder.vbx_links.pack_start(lnk, False, True, 0)
                link_added = True

        if link_added:
            space = Gtk.Alignment.new(0, 0, 0, 0)
            space.set_visible(True)
            space.set_vexpand(True)
            self._builder.vbx_links.pack_start(space, False, True, 0)

        return link_added

    def _show_problem_message(self, message):
        msg = Gtk.Label.new(message)
        msg.set_markup(message)
        msg.set_visible(True)
        msg.set_halign(Gtk.Align.START)
        msg.set_valign(Gtk.Align.START)
        msg.set_line_wrap(True)

        self._builder.vbx_problem_messages.pack_start(msg, False, True, 0)

    @handle_problem_and_source_errors
    def _set_problem(self, problem):
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

            if app.name:
                self._builder.lbl_reason.set_text("{0} {1}".format(
                        app.name, _(' crashed').strip()))
            else:
                # If Application's name is unknown, display neutral
                # header "'Type' problem has been detected":
                #  Kerneloops problem has been detected
                #  CCpp problem has been detected
                #  Python problem has been detected
                #  Ruby problem has been detected
                #  VMCore problem has been detected
                #  AVC problem has been detected
                #  Java problem has been detected
                self._builder.lbl_reason.set_text(
                        _("{0} problem has been detected").format(
                                problem['type']))

            self._builder.lbl_app_version_value.set_text(
                        problem['package'] or _("N/A"))
            self._builder.lbl_detected_value.set_text(
                        problem['date'].strftime(
                            locale.nl_langinfo(locale.D_FMT)))

            if app.icon:
                self._builder.img_app_icon.set_from_pixbuf(app.icon)
            else:
                self._builder.img_app_icon.clear()

            self._builder.lbl_reported.set_text(_("Reported"))
            if problem['not-reportable']:
                self._builder.lbl_reported_value.set_text(
                        _('cannot be reported'))
                self._show_problem_links(problem['submission'])
                self._show_problem_message(problem['not-reportable'])
            elif problem['is_reported']:
                if self._show_problem_links(problem['submission']):
                    self._builder.lbl_reported.set_text(_("Reports"))
                    self._builder.lbl_reported_value.set_text('')

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

    @handle_problem_and_source_errors
    def on_gac_delete_activate(self, action):
        for prblm in self._get_selected(self._builder.tvs_problems):
            try:
                self._controller.delete(prblm)
            except errors.InvalidProblem as ex:
                logging.debug(traceback.format_exc())
                self._remove_problem_from_storage(ex.problem_id)

    @handle_problem_and_source_errors
    def on_gac_detail_activate(self, action):
        selected = self._get_selected(self._builder.tvs_problems)
        if selected:
            self._controller.detail(selected[0])

    @handle_problem_and_source_errors
    def on_gac_report_activate(self, action):
        selected = self._get_selected(self._builder.tvs_problems)
        if selected and not selected[0]['not-reportable']:
            self._controller.report(selected[0])

    @handle_problem_and_source_errors
    def on_te_search_changed(self, entry):
        self._filter.set_pattern(entry.get_text())

    def on_gac_opt_all_problems_activate(self, action):
        conf = config.get_configuration()
        conf['all_problems'] = self._builder.chb_all_problems.get_active()

    def on_gac_control_preferences_activate(self, action):
        wrappers.show_events_list_dialog(self)

    def on_gac_open_directory_activate(self, action):
        selection = self._get_selected(self._builder.tvs_problems)
        if selection:
            subprocess.Popen(["xdg-open", selection[0].problem_id])
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
