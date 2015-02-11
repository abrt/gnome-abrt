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
#include <common.h>
#include <libreport/problem_utils.h>
#include <pygobject.h>

PyObject *p_get_app_for_cmdline(PyObject *module, PyObject *args)
{
    (void)module;

    const char *dir_str = NULL;
    if (PyArg_ParseTuple(args, "s", &dir_str))
    {
        GAppInfo *app = problem_create_app_from_cmdline(dir_str);
        if (app)
            return pygobject_new((GObject *)app);
    }

    Py_RETURN_NONE;
}
