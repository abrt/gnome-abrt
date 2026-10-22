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
import subprocess
from gi.repository import Gio


def get_app_for_cmdline(cmdline):
    """Find GAppInfo matching cmdline executable name using native GIO."""
    if not cmdline:
        return None
    argv = cmdline.strip().split()
    if not argv:
        return None
    exe_name = os.path.basename(argv[0])

    for app in Gio.AppInfo.get_all():
        executable = app.get_executable()
        if executable and os.path.basename(executable) == exe_name:
            return app
        id_ = app.get_id()
        if id_ and id_.lower().startswith(exe_name.lower()):
            return app
    return None


def get_app_for_env(env_list, pid):
    """Find GAppInfo from GIO_LAUNCHED_DESKTOP_FILE in environment."""
    env_dict = {}
    for item in env_list:
        if '=' in item:
            k, v = item.split('=', 1)
            env_dict[k] = v

    launched_pid = env_dict.get('GIO_LAUNCHED_DESKTOP_FILE_PID')
    desktop_file = env_dict.get('GIO_LAUNCHED_DESKTOP_FILE')
    if desktop_file and launched_pid:
        try:
            if int(launched_pid) == pid:
                if desktop_file.startswith('/'):
                    return Gio.DesktopAppInfo.new_from_filename(desktop_file)
                return Gio.DesktopAppInfo.new(desktop_file)
        except (ValueError, TypeError):
            pass
    return None


def show_events_list_dialog(parent_window=None):
    """Launch system-config-abrt as an external process if available."""
    try:
        subprocess.Popen(['system-config-abrt'])
    except Exception:
        pass


def show_problem_details_for_dir(problem_dir, parent_window=None):
    """Obsolete in GTK4 port: details are shown directly in main window."""
    pass
