import datetime
import calendar

from l10n import _

def fancydate(value, base_date=None):
    """
    Converts a date to a fancy string
    """
    if not base_date:
        base_date = datetime.datetime.now()

    old_date = value

    if base_date < old_date:
        return _('Future')

    d = base_date - old_date

    if d.days == 0:
        # TODO add l10n
        return "%d:%d" % (old_date.hour, old_date.minute)
    elif d.days == 1:
        return _('Yesterday')

    # this week - return a name of a day
    if d.days < base_date.isoweekday():
        # TODO test l10n
        return calendar.day_name[base_date.weekday() - d.days]

    if old_date.month == base_date.month and old_date.year == base_date.year:
        # computes a number of calendar weeks (not only 7 days)
        offset = int(round((d.days - base_date.isoweekday())/7, 0)) + 1;
        name = _('week')
    elif old_date.year == base_date.year:
        offset = base_date.month - old_date.month
        name = _('month')
    else:
        offset = base_date.year - old_date.year
        name = _('year')

    if offset == 1:
        return _("Last {0!s}").format(name);

    return _("{0:d} {1!s}s ago").format(offset, name);
