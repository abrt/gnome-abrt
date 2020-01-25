/*
    Copyright (C) 2014  Abrt team.
    Copyright (C) 2014  RedHat inc.

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
#include "common.h"
#include <libreport/internal_libreport_gtk.h>
#define NO_IMPORT_PYGOBJECT
#include <pygobject.h>
#include <libabrt.h>

PyObject *p_show_problem_details_for_dir(PyObject *module, PyObject *args)
{
    (void)module;

    const char *dir_str = NULL;
    PyGObject *pygtkwnd = NULL;
    if (PyArg_ParseTuple(args, "s|O", &dir_str, &pygtkwnd))
    {
        problem_data_t *problem_data = get_full_problem_data_over_dbus(dir_str);

        /* get_full_problem_data_over_dbus() printed an error message */
        if (problem_data == ERR_PTR || problem_data == NULL)
            Py_RETURN_NONE;

        GtkWindow *wnd = pygtkwnd ? GTK_WINDOW(pygtkwnd->obj) : NULL;
        GtkWidget *dialog = problem_details_dialog_new(problem_data, wnd);

        if (dialog != NULL)
            gtk_dialog_run(GTK_DIALOG(dialog));
    }

    Py_RETURN_NONE;
}
