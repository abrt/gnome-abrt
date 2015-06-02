/*
    Copyright (C) 2015  Abrt team.
    Copyright (C) 2015  RedHat inc.

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
#include <X11/Xlib.h>

PyObject *p_can_connect_to_xserver(PyObject *module, PyObject *args)
{
    (void)module;
    (void)args;

    Display *d = XOpenDisplay(NULL);
    if (d == NULL)
        Py_RETURN_FALSE;

    XCloseDisplay(d);

    Py_RETURN_TRUE;
}

