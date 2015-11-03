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

import datetime
import calendar
import logging

#pylint: disable=E0611
from gi.repository import GLib
#pylint: disable=E0611
from gi.repository import Gtk
#pylint: disable=E0611
from gi.repository import Gdk

from gnome_abrt.l10n import _
from gnome_abrt.l10n import ngettext
from gnome_abrt.config import get_configuration

def fancydate(value, base_date=None):
    """
    Converts a date to a fancy string
    """
    if not base_date:
        base_date = datetime.datetime.now()

    old_date = value
    if base_date < old_date:
        return _('Future')

    tmdt = base_date.date() - old_date.date()

    if tmdt.days == 0:
        return old_date.time().strftime(get_configuration()['T_FMT'])
    elif tmdt.days == 1:
        return _('Yesterday')

    # this week - return a name of a day
    if tmdt.days < base_date.isoweekday():
        return calendar.day_name[base_date.weekday() - tmdt.days]

    if old_date.month == base_date.month and old_date.year == base_date.year:
        # computes a number of calendar weeks (not only 7 days)
        # Note: the offset will never be negative nor zero because
        # negative means the future and 0 means today, these cases
        # have been handled few lines above. The same rule is true
        # for the code below.
        offset = int(round((tmdt.days - base_date.isoweekday())/7, 0)) + 1
        if offset == 1:
            return _('Last week')
        # Translators: This message will never be used for less than
        # 2 weeks ago nor for more than one month ago. However, the singular
        # form is necessary for some languages which do not have plural.
        msg = ngettext('{0:d} week ago', '{0:d} weeks ago', offset)
        return msg.format(offset)
    elif old_date.year == base_date.year:
        offset = base_date.month - old_date.month
        if offset == 1:
            return _('Last month')
        # Translators: This message will never be used for less than
        # 2 months ago nor for more than one year ago. See the comment above.
        msg = ngettext('{0:d} month ago', '{0:d} months ago', offset)
        return msg.format(offset)
    else:
        offset = base_date.year - old_date.year
        if offset == 1:
            return _('Last year')
        # Translators: This message will never be used for less than
        # 2 years ago. However, the singular form is necessary for some
        # languages which do not have plural (Chinese, Japanese, Korean)
        # or reuse the singular form for some plural cases (21 in Russian).
        msg = ngettext('{0:d} year ago', '{0:d} years ago', offset)
        return msg.format(offset)


def smart_truncate(content, length=100, suffix='...'):
    if len(content) <= length:
        return content
    else:
        return content[:length].rsplit(' ', 1)[0] + suffix


def load_icon(name=None, gicon=None, scale=1):
    theme = Gtk.IconTheme.get_default()

    icon = None
    if not gicon is None and name is None:
        name = gicon.to_string()
        icon = theme.lookup_by_gicon_for_scale(gicon, 128, scale,
                                        Gtk.IconLookupFlags.FORCE_SIZE)
    elif not name is None and gicon is None:
        icon = theme.lookup_icon_for_scale(name, 128, scale,
                                        Gtk.IconLookupFlags.FORCE_SIZE
                                        | Gtk.IconLookupFlags.FORCE_SYMBOLIC)
    else:
        logging.error("BUG: invalid arguments in load_icon():" \
                      "name={0}, gicon={1}, scale={2}"
                      .format(str(name), str(gicon), str(scale)))
        return None

    if icon is None:
        logging.warning(_("Failed to find icon '{0}'").format(name))
        return None

    try:
        return icon.load_icon()
    #pylint: disable=E0712
    except GLib.Error as ex:
        logging.warning(_("Failed to load icon '{0}': {1}")
                            .format(name, str(ex)))

    return None


def set_icon_from_pixbuf_with_scale(icon, pixbuf, scale=1):
    if scale == 1 or scale is None or pixbuf is None:
        icon.set_from_pixbuf(pixbuf)
        return None

    surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale, None)
    icon.set_from_surface(surface)
    return None
