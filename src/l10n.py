import gettext
import locale

GETTEXT_PROGNAME = "gnome-abrt"
PROGNAME = "gnome-abrt"

import locale
import gettext

_ = lambda x: gettext.lgettext(x)

def init(progname):
    global PROGNAME
    PROGNAME = progname
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        import os
        os.environ['LC_ALL'] = 'C'
        locale.setlocale(locale.LC_ALL, "")

    gettext.bind_textdomain_codeset(GETTEXT_PROGNAME, locale.nl_langinfo(locale.CODESET))
    # TODO: configurable path to the binary
    gettext.bindtextdomain(GETTEXT_PROGNAME, '/usr/share/locale')
    gettext.textdomain(GETTEXT_PROGNAME)
