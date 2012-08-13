import datetime
import calendar

def fancydate(value, base_date=None):
    """
    Converts a date to a fancy string
    """
    if not base_date:
        base_date = datetime.datetime.now()

    old_date = value

    if base_date < old_date:
        return 'Future'

    d = base_date - old_date

    if d.days == 0:
        return "%d:%d" % (old_date.hour, old_date.minute)
    elif d.days == 1:
        return 'Yesterday'

    # this week - return a name of a day
    if d.days < base_date.isoweekday():
        return calendar.day_name[base_date.weekday() - d.days]

    if old_date.month == base_date.month and old_date.year == base_date.year:
        # computes a number of calendar weeks (not only 7 days)
        offset = round((d.days - base_date.isoweekday())/7, 0) + 1;
        name = 'week'
    elif old_date.year == base_date.year:
        offset = base_date.month - old_date.month
        name = 'month'
    else:
        offset = base_date.year - old_date.year
        name = 'year'

    if offset == 1:
        return "Last %s" % (name);

    return "%d %ss ago" % (offset, name);
