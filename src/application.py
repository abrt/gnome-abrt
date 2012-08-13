import os
import sys

# PyGObject
from gi.repository import Gtk
from gi.repository import Gio

class Application(object):

    def __init__(self, executable, name=None, icon=None):
        self.executable = executable

        if name:
            self.name = name
        else:
            self.name = executable

        self.icon = icon

__globa_app_cache__ = {}

def find_application(component, executable):
    global __globa_app_cache__

    if not executable in __globa_app_cache__:
        if executable and len(executable) > 0:
            lookup_exec = os.path.basename(executable)
            ll = len(lookup_exec)
            for dai in Gio.DesktopAppInfo.get_all():
                if dai.get_executable()[:ll] == lookup_exec:
                    __globa_app_cache__[executable] = Application(executable,
                                                                  name=dai.get_name(),
                                                                  icon=Gtk.IconTheme.get_default().load_icon(dai.get_icon().get_names()[0], 48, Gtk.IconLookupFlags.USE_BUILTIN))
                    return __globa_app_cache__[executable]
        __globa_app_cache__[executable] = Application(executable, name=component)

    return __globa_app_cache__[executable]
