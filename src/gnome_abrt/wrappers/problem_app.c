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

PyObject *p_get_app_for_env(PyObject *module, PyObject *args)
{
    (void)module;

    PyObject *envp_seq;
    pid_t pid = -1;
    if (PyArg_ParseTuple(args, "Oi", &envp_seq, &pid) &&
        (envp_seq = PySequence_Fast(envp_seq, "expected a sequence")))
    {
        GPtrArray *envp_array;
        int size, i;

        size = PySequence_Size(envp_seq);
        envp_array = g_ptr_array_new_full(size + 1, g_free);

        for (i = 0; i < size; i++) {
            PyObject *seqItem = PySequence_Fast_GET_ITEM(envp_seq, i);

            const char *strItem = PyUnicode_AsUTF8(seqItem);
            if (strItem == NULL)
            {
                PyObject *unicodeObj = PyObject_Str(seqItem);
                const char *str = PyUnicode_AsUTF8(unicodeObj);

                fprintf(stderr, "BUG:%s:%d: failed to get a UTF-8 string from: %s\n", __FILE__, __LINE__, str);
                /* Catch all exceptions, print them out and continue in
                 * processing (try, catch, log, continue). */
                PyErr_Print();
                PyErr_Clear();
                continue;
            }

            g_ptr_array_insert (envp_array, -1, g_strdup(strItem));
        }
        g_ptr_array_insert (envp_array, -1, NULL);

        GAppInfo *app = problem_create_app_from_env((const char **) envp_array->pdata, pid);
        g_ptr_array_free(envp_array, TRUE);
        if (app)
            return pygobject_new((GObject *)app);
    }

    Py_RETURN_NONE;
}
