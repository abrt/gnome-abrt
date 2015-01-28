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
#include "common.h"
#include <pygobject.h>

static char module_doc[] = "gnome-abrt's libreport & abrt wrappers";

static PyMethodDef module_methods[] = {
    /* method_name, func, flags, doc_string */
    { "show_events_list_dialog", p_show_events_list_dialog, METH_VARARGS, "Open a dialog with event configurations" },
    { "show_system_config_abrt_dialog", p_show_system_config_abrt_dialog, METH_VARARGS, "Open a dialog with ABRT configuration" },
    { "show_problem_details_for_dir", p_show_problem_details_for_dir, METH_VARARGS, "Open a dialog with technical details" },
    { "get_app_for_cmdline", p_get_app_for_cmdline, METH_VARARGS, "Get the application for a specific command-line" },
    { NULL }
};

PyMODINIT_FUNC PyInit__wrappers(void)
{
    PyObject *m;
    static struct PyModuleDef moduledef = {
            .m_base = PyModuleDef_HEAD_INIT,
            .m_name = "_wrappers",
            .m_doc = module_doc,
            .m_size = -1,
            .m_methods = module_methods,
            .m_reload = NULL,
            .m_traverse = NULL,
            .m_clear = NULL,
            .m_free = NULL,
    };
    m = PyModule_Create(&moduledef);

    if (m == NULL)
        return NULL;

    Py_Initialize();
    pygobject_init(-1, -1, -1);

    return m;
}
