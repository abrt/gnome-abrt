import os
import xdg

import problems
import dbus_problems
import config

def dump_problems(source):
    for p in v.get_problems():
        print p, p['component'], p['type']
        #, p.get_application().name, p['type']

class SourceObserver:
    def __init__(self):
        pass

    def problem_source_updated(self, source):
        print "--- Updated source start ----"
        dump_problems(source)
        print "--- Updated source end ----"


conf = config.get_configuration()
conf.add_option("all_problems", default_value=False)

observer = SourceObserver()
sources = { "DBus" : dbus_problems.DBusProblemSource() }


for k, v in sources.items():
    print "---- Source %s start ----" % (k)
    v.attach(observer)
    dump_problems(v)
    print "---- Source %s end ----" % (k)

conf['all_problems'] = True
