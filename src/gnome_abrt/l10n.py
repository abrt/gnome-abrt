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

import gettext
import locale

GETTEXT_PROGNAME = None

_ = gettext.lgettext

def init(progname, localedir='/usr/share/locale'):
    global GETTEXT_PROGNAME
    GETTEXT_PROGNAME = progname
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        import os
        os.environ['LC_ALL'] = 'C'
        locale.setlocale(locale.LC_ALL, "")

    gettext.bind_textdomain_codeset(progname,
                                    locale.nl_langinfo(locale.CODESET))
    gettext.bindtextdomain(progname, localedir)
    gettext.textdomain(progname)
