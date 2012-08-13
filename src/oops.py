#!/usr/bin/python

import os
import sys

# pygobject
from gi.repository import Gtk

# pyxdg
import xdg
import xdg.BaseDirectory

# oops
import config
import views
import problems
import dbus_problems
import directory_problems
import controller

class OopsApplication(Gtk.Application):
    
    def __init__(self):
        super(OopsApplication, self).__init__()

        conf = config.get_configuration()
        conf.add_option("all_problems", default_value=False)

        self.source = problems.MultipleSources(dbus_problems.DBusProblemSource(),
                                               # TODO : use pyxdg-0.21 save_cache_path()
                                               directory_problems.DirectoryProblemSource(os.path.join(xdg.BaseDirectory.xdg_cache_home, "abrt/spool")))

    def do_activate(self):
        self.window = views.OopsWindow(self, self.source, controller.Controller())
        self.window.connect("delete-event", self.on_window_delete_event)
        self.window.show_all()

    def on_window_delete_event(self, widget, data):
        self.quit()


if __name__ == "__main__":
    app = OopsApplication()
    exit_code = app.run(sys.argv)
    sys.exit(exit_code)
