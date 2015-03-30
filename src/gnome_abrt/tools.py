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
        offset = int(round((tmdt.days - base_date.isoweekday())/7, 0)) + 1
        return ngettext('Last week', '{0:d} weeks ago', offset).format(offset)
    elif old_date.year == base_date.year:
        offset = base_date.month - old_date.month
        return ngettext('Last month', '{0:d} months ago', offset).format(offset)
    else:
        offset = base_date.year - old_date.year
        return ngettext('Last year', '{0:d} years ago', offset).format(offset)


def smart_truncate(content, length=100, suffix='...'):
    if len(content) <= length:
        return content
    else:
        return content[:length].rsplit(' ', 1)[0] + suffix
