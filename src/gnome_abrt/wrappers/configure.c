/*
    Copyright (C) 2012  Abrt team.
    Copyright (C) 2012  RedHat inc.

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Suite 500, Boston, MA  02110-1335  USA
*/
#include <common.h>
#include <libreport/internal_libreport_gtk.h>
#include <abrt/system-config-abrt.h>
#include <pygobject.h>

PyObject *p_show_events_list_dialog(PyObject *module, PyObject *args)
{
    (void)module;

    PyGObject *pygtkwnd = NULL;
    if (PyArg_ParseTuple(args, "|O", &pygtkwnd))
    {
        GtkWindow *wnd = pygtkwnd ? GTK_WINDOW(pygtkwnd->obj) : NULL;
        show_config_list_dialog(wnd);
    }

    Py_RETURN_NONE;
}

PyObject *p_show_system_config_abrt_dialog(PyObject *module, PyObject *args)
{
    (void)module;

    PyGObject *pygtkwnd = NULL;
    if (PyArg_ParseTuple(args, "|O", &pygtkwnd))
    {
        GtkWindow *wnd = pygtkwnd ? GTK_WINDOW(pygtkwnd->obj) : NULL;
        show_system_config_abrt_dialog(wnd);
    }

    Py_RETURN_NONE;
}
