import datetime

from math import ceil
from enum import Enum
from collections import namedtuple


class Bounds(namedtuple('Bound', ("min", "max")), Enum):
    minute = (0, 59)
    hour = (0, 23)
    dom = (1, 31)
    month = (1, 12)
    dow = (1, 7)

    def range(self, step=1):
        return Range(self.min, self.max, step)


class Job:

    """
    Represents a cron job. This handles parsing of the job to get timing
    information, as well as determining when the job will be run next.
    >>> import parser
    >>> job = parser.parse_job("* * * * * true")
    >>> (job.mins, job.hours, job.doms, job.months, job.dows)
    (0-59/1, 0-23/1, 1-31/1, 1-12/1, 1-7/1)
    >>> parser.parse_job("* * * * * true").job
    'true'
    >>> parser.parse_job("* * * * * echo test").job
    'echo test'
    """

    def __init__(self, times, job):
        (self.mins, self.hours, self.doms, self.months, self.dows) = times
        self.job = job

    def next_value(self, dt):
        """
        Returns the next time this cron job will run.
        >>> import parser
        >>> parser.parse_job("* * * * * true").next_value(
        ...     datetime.datetime(2014, 11, 15, 17, 4, 49))
        datetime.datetime(2014, 11, 15, 17, 5)
        >>> parser.parse_job("* * 1 * * true").next_value(
        ...     datetime.datetime(2014, 11, 15, 17, 4, 49))
        datetime.datetime(2014, 12, 1, 0, 0)
        >>> parser.parse_job("* * * * 3 true").next_value(
        ...     datetime.datetime(2014, 11, 15, 17, 4, 49))
        datetime.datetime(2014, 11, 19, 0, 0)
        >>> parser.parse_job("* * * * 3 true").next_value(
        ...     datetime.datetime(2014, 11, 29, 17, 4, 49))
        datetime.datetime(2014, 12, 3, 0, 0)
        >>> parser.parse_job("* * * 11 3 true").next_value(
        ...     datetime.datetime(2014, 11, 29, 17, 4, 49))
        datetime.datetime(2015, 11, 4, 0, 0)
        >>> end_of_year = datetime.datetime(2014, 12, 31, 23, 59)
        >>> parser.parse_job("* * * * * true").next_value(end_of_year)
        datetime.datetime(2015, 1, 1, 0, 0)
        >>> parser.parse_job("* * 29 2 * true").next_value(end_of_year)
        datetime.datetime(2016, 2, 29, 0, 0)
        >>> parser.parse_job("* * 29 2 * true").next_value(
        ...     datetime.datetime(2196, 2, 29, 23, 59))
        datetime.datetime(2204, 2, 29, 0, 0)
        """
        #dt.minute, dt.hour, dt.day, dt.month, dt.isoweekday(), dt.year)
        dt = dt.replace(second=0)

        def find_minute_hour(dt, minute_carry=True):
            minute_carry, next_minute = self.mins.next_value(
                dt.minute, minute_carry)
            hour_carry, next_hour = self.hours.next_value(
                dt.hour, minute_carry)
            if hour_carry:
                _, next_minute = self.mins.next_value(0, carry=False)
            try:
                return (hour_carry,
                        dt.replace(hour=next_hour, minute=next_minute))
            except:
                raise ValueError(
                    "Couldn't find a valid time for the cron job") from None

        def find_dom_month_year(dt, hour_carry):
            dom = dt.day
            month = dt.month
            year = dt.year
            for i in range(100):
                dom_carry, dom = self.doms.next_value(dom, hour_carry)
                month_carry, month = self.months.next_value(month, dom_carry)
                year += month_carry
                if month_carry:
                    dom_carry, dom = self.doms.next_value(0, carry=False)
                try:
                    return (dom_carry or month_carry,
                            dt.replace(year=year, month=month, day=dom))
                except ValueError:
                    continue  # There should be something here
            raise ValueError("Couldn't find a valid time for the cron job")

        def find_dow_month_year(dt, hour_carry):
            old_dow = dt.isoweekday() % 7
            month = dt.month
            dow_carry, dow = self.dows.next_value(
                old_dow, carry=hour_carry)
            delta = _dows_to_timedelta(old_dow, dow)
            month_carry, next_month = self.months.next_value(
                month, carry=False)
            if (dt + delta).month == month and next_month == month:
                return dow_carry, dt + delta

            month_carry, next_month = self.months.next_value(month, carry=True)
            dt = dt.replace(year=dt.year+month_carry,
                            month=next_month, day=1)

            tmp_dow = dt.isoweekday() % 7
            _, dow = self.dows.next_value(tmp_dow, carry=False)
            return True, dt + _dows_to_timedelta(tmp_dow, dow)

        hour_carry, time = find_minute_hour(dt)
        dom_dt, dow_dt = (find_minute_hour(
            dt.replace(hour=0, minute=0), minute_carry=False)[1]
            if high_carry else dt
            for high_carry, dt in (find_dom_month_year(time, hour_carry),
                                   find_dow_month_year(time, hour_carry)))

        if self.dow_specified and self.dom_specified:
            return min(dom_dt, dow_dt)
        elif self.dow_specified and not self.dom_specified:
            return dow_dt
        else:
            return dom_dt


def _dows_to_timedelta(current, next):
    return datetime.timedelta(
        days=next-current, weeks=1 if next < current else 0)


class Set:

    """
    Represents a set of ranges in one particular field of one particular
    job.
    >>> Set((Range(1, 5, 4), Range(34, 57, 59), Range(59,59),
    ...      Range(0, 59, 30)))
    1-5/4,34-57/59,59-59/1,0-59/30
    """

    def __init__(self, ranges):
        self.ranges = ranges

    def __repr__(self):
        return ','.join(str(r) for r in self.ranges)

    def next_value(self, current, carry=True):
        """
        Finds the next occurring time for a set of ranges. This should
        be the first of the next_values of all of the ranges in the set.
        >>> Set((Range(1, 5, 4), Range(34, 57, 59), Range(59,59),
        ...      Range(0, 59, 30))).next_value(23)
        (False, 30)
        >>> Set((Range(1, 4), Range(3, 7))).next_value(8)
        (True, 1)
        """
        return min(r.next_value(current, carry) for r in self.ranges)

    def __eq__(self, other):
        return self.ranges == other.ranges


class Range:

    """
    Represents a range of times, plus an optional step value.
    """

    def __init__(self, min, max, step=1):
        self.min = min
        self.max = max
        self.step = step

    def __repr__(self):
        return '{}-{}/{}'.format(self.min, self.max, self.step)

    def next_value(self, current, carry=True):
        """
        Returns the following value that this particular range will be
        triggered on, as well as a bool indicating if the range had to
        wrap around to reach this value.
        >>> all_minutes = Bounds.minute.range()
        >>> all_minutes.next_value(4)
        (False, 5)
        >>> all_minutes.next_value(59)
        (True, 0)
        >>> all_hours = Bounds.hour.range()
        >>> all_hours.next_value(23, carry=False)
        (False, 23)
        >>> all_hours.next_value(23, carry=True)
        (True, 0)
        >>> all_hours.next_value(24, carry=True)
        (True, 0)
        >>> all_hours.next_value(0, carry=False)
        (False, 0)
        >>> Range(5, 20, 11).next_value(17)
        (True, 5)
        >>> Range(5, 20, 11).next_value(11)
        (False, 16)
        >>> Range(59, 60, 29).next_value(3)
        (False, 59)
        >>> Range(29, 60, 29).next_value(3)
        (False, 29)
        """
        distance = ceil((current + carry - self.min)/self.step)
        next = self.min + self.step*distance
        if current+carry <= self.min:
            return (False, self.min)
        elif next > self.max:
            return (True, self.min)
        else:
            return (False, next)

    def validate(self, current, carry=True):
        """
        Computes the exact same thing as next_value is supposed to
        because next_value uses math that I'm not quite sure of
        >>> from random import randint
        >>> for i in range(1000):
        ...     min = randint(0, 59)
        ...     v = Range(min, randint(min, 59),
        ...             randint(1, 59))
        ...     s = randint(0, 59)
        ...     c = randint(0, 1)
        ...     assert v.next_value(s, c) == v.validate(s, c), (
        ...             v, v.next_value(s, c), v.validate(s, c))
        """
        if current+carry < self.min:
            return (False, self.min)
        for i in range(self.min, self.max+1, self.step):
            if i >= current+carry:
                return (False, i)
        return (True, self.min)

    def __eq__(self, other):
        return (self.min == other.min
                and self.max == other.max
                and self.step == other.step)

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
