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

static PyMethodDef module_methods[] = {
    /* method_name, func, flags, doc_string */
    { "show_events_list_dialog", p_show_events_list_dialog, METH_VARARGS, "Open a dialog with event configurations" },
    { "show_system_config_abrt_dialog", p_show_system_config_abrt_dialog, METH_VARARGS, "Open a dialog with ABRT configuration" },
    { NULL }
};

#ifndef PyMODINIT_FUNC /* declarations for DLL import/export */
#warning "PyMODINIT_FUNC ndef"
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
init_wrappers(void)
{
    if (!Py_InitModule("_wrappers", module_methods))
        printf("Py_InitModule() == NULL\n");
}
