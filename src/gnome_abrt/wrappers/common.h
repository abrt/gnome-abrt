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
#include <Python.h>

/* module-level functions */
PyObject *p_show_events_list_dialog(PyObject *module, PyObject *args);

/* Problem Details */
PyObject *p_show_problem_details_for_dir(PyObject *module, PyObject *args);

/* App for a command-line */
PyObject *p_get_app_for_cmdline(PyObject *module, PyObject *args);

/* App for an env */
PyObject *p_get_app_for_env(PyObject *module, PyObject *args);
