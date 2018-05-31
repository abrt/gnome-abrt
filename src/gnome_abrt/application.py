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

import os
from gnome_abrt import wrappers

class Application(object):

    def __init__(self, executable, name=None, icon=None):
        self.executable = executable or "N/A"

        if name:
            self.name = name
        elif executable:
            self.name = os.path.basename(executable)
        else:
            self.name = None

        self.icon = icon


def find_application(cmdline, envp, pid, component):
    app = None
    if envp:
        app = wrappers.get_app_for_env(envp.split('\n'), int(pid))
    if not app and cmdline:
        app = wrappers.get_app_for_cmdline(cmdline)
    if not app:
        return Application(cmdline.split(" ")[0] if cmdline else None,
                           name=component)

    ret = Application(app.get_executable(),
            name=app.get_name(), icon=app.get_icon())

    return ret
