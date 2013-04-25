# coding=UTF-8

## Copyright (C) 2013 ABRT team <abrt-devel-list@redhat.com>
## Copyright (C) 2013 Red Hat, Inc.

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

import gnome_abrt
from gnome_abrt.l10n import _

# libreport
from report import problem_data, report_problem_in_memory, LIBREPORT_NOWAIT

# pygogject
#pylint: disable=E0611
from gi.repository import Gtk


def _show_error_dialog(parent, summary, description):
    dialog = Gtk.MessageDialog(parent, Gtk.DialogFlags.DESTROY_WITH_PARENT,
                               Gtk.MessageType.ERROR,
                               Gtk.ButtonsType.OK,
                               summary)

    dialog.format_secondary_text(description)

    dialog.run()
    dialog.destroy()

def _on_button_send_cb(button, dialog):
    buf = dialog.tev.get_buffer()
    it_start = buf.get_start_iter()
    it_end = buf.get_end_iter()
    description = buf.get_text(it_start, it_end, False)

    if len(description) < 10:
        _show_error_dialog(dialog,
                _("The description of problem is too short"),
                _("In order to get more useful reports we "
                    "do not accept reports with the description "
                    "shorter than 10 letters."))

        dialog.tev.grab_focus()
        return

    summary = dialog.txe_reason.get_text()
    if len(summary) < 10:
        _show_error_dialog(dialog,
                _("The summary of problem is too short"),
                _("In order to get more useful reports we "
                    "do not accept reports with the summary "
                    "shorter than 10 letters."))

        dialog.txe_reason.grab_focus()
        dialog.txe_reason.set_position(len(summary))
        return

    dialog.destroy()

    report = problem_data()
    report.add("reason", summary)
    report.add("comment", description)
    report.add("component", gnome_abrt.PACKAGE)
    report.add("package",
            "{0}-{1}".format(gnome_abrt.PACKAGE, gnome_abrt.VERSION))

    report.add_basics()
    report.add("duphash", report.get("uuid")[0])


    report_problem_in_memory(report, LIBREPORT_NOWAIT)


def show_report_problem_with_abrt():
    wnd_report = Gtk.Window(Gtk.WindowType.TOPLEVEL)
    wnd_report.set_title(_("Problem description"))
    wnd_report.set_default_size(400, 400)

    wnd_report.vbox = Gtk.VBox(0)
    wnd_report.vbox.set_margin_top(5)
    wnd_report.vbox.set_margin_left(5)
    wnd_report.vbox.set_margin_right(5)

    wnd_report.lbl_summary = Gtk.Label(_("Summary:"))
    wnd_report.lbl_summary.set_halign(Gtk.Align.START)
    wnd_report.lbl_summary.set_margin_left(3)
    wnd_report.lbl_summary.set_margin_right(3)

    wnd_report.txe_reason = Gtk.Entry()

    wnd_report.tev = Gtk.TextView()
    wnd_report.tev.set_margin_left(3)
    wnd_report.tev.set_margin_right(3)
    wnd_report.tev.set_can_focus(True)

    wnd_report.btn_send = Gtk.Button(_("_Send"))
    wnd_report.btn_send.set_use_underline(True)
    wnd_report.btn_send.connect("clicked", _on_button_send_cb, wnd_report)

    wnd_report.vbox.pack_start(wnd_report.lbl_summary, False, True, 3)
    wnd_report.vbox.pack_start(wnd_report.txe_reason,  False, True, 3)
    wnd_report.vbox.pack_start(wnd_report.tev,          True, True, 5)
    wnd_report.vbox.pack_start(wnd_report.btn_send,    False, True, 3)

    wnd_report.add(wnd_report.vbox)

    wnd_report.show_all()

    # Sets text but text is selected :)
    wnd_report.txe_reason.set_text(_("A problem with ABRT"))
    # Unselect text in txe_entry
    wnd_report.txe_reason.set_position(0)

    # Move focus to text view with description of problem
    wnd_report.tev.grab_focus()
