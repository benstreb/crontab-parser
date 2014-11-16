"""
This file parses Crontabs in order to manipulate them
>>> from io import StringIO
>>> Crontab(StringIO("#comment\\n  \t\\nVAR=3\\n* * * * * true"))
<__main__.Crontab object at 0x...>
"""

import re
import datetime
from math import ceil


class Crontab:

    """
    Parses a crontab looking for jobs. We only care about jobs for this
    task, so we're ignoring environment variables as well as comments and
    blank lines.
    >>> from io import StringIO
    >>> Crontab(StringIO("* * * * * true")).jobs
    [<__main__.Job object at 0x...>]
    """

    def __init__(self, file):
        self.jobs = []
        lineno = 0
        try:
            for line in file:
                lineno += 1
                line = line.strip()
                if (len(line) == 0 or line.startswith("#") or
                        re.match("\w+\s*=", line)):
                    continue
                else:
                    self.jobs.append(Job(line))
        except CronSyntaxError as e:
            e.lineno = lineno
            raise

    def next_runs(self, now=None):
        """
        Returns a generator yielding a tuple containing each job as a
        string and when it's next expected to run as a datetime.
        >>> from io import StringIO
        >>> tuple(Crontab(StringIO("0 * * * * true\\n0 0 * * * false")
        ...               ).next_runs(
        ...     datetime.datetime(2014, 11, 15, 17, 4))) == (
        ...     ('true', datetime.datetime(2014, 11, 15, 18, 0)),
        ...     ('false', datetime.datetime(2014, 11, 16, 0, 0)))
        True
        >>> now = datetime.datetime.now()
        >>> run = tuple(Crontab(StringIO("* * * * * true")).next_runs())
        """
        if now is None:
            now = datetime.datetime.now()
        return ((job.job, job.next_value(now)) for job in self.jobs)


class Job:

    """
    Represents a cron job. This handles parsing of the job to get timing
    information, as well as determining when the job will be run next.
    >>> job = Job("* * * * * true")
    >>> (job.mins, job.hours, job.doms, job.months, job.dows)
    (0-59/1, 0-23/1, 1-31/1, 1-12/1, 1-7/1)
    >>> Job("* * * * * true").job
    'true'
    >>> Job("* * * * * echo test").job
    'echo test'
    """

    MINUTE_RANGE = (0, 59)
    HOUR_RANGE = (0, 23)
    DOM_RANGE = (1, 31)
    MONTH_RANGE = (1, 12)
    DOW_RANGE = (1, 7)
    STAR_RANGES = (
        MINUTE_RANGE,
        HOUR_RANGE,
        DOM_RANGE,
        MONTH_RANGE,
        DOW_RANGE)

    def __init__(self, raw_line):
        line = raw_line.split(maxsplit=5)
        try:
            (self.mins, self.hours, self.doms, self.months, self.dows) = tuple(
                Set(f, r) for f, r in zip(line, Job.STAR_RANGES))
            self.dom_specified = line[2] != '*'
            self.dow_specified = line[4] != '*'
        except ValueError:
            raise CronSyntaxError("Invalid job", (raw_line, -1, -1, raw_line))
        self.job = line[5]

    def next_value(self, dt):
        """
        Returns the next time this cron job will run.
        >>> Job("* * * * * true").next_value(
        ...     datetime.datetime(2014, 11, 15, 17, 4, 49))
        datetime.datetime(2014, 11, 15, 17, 5)
        >>> end_of_year = datetime.datetime(2014, 12, 31, 23, 59)
        >>> Job("* * * * * true").next_value(end_of_year)
        datetime.datetime(2015, 1, 1, 0, 0)
        >>> Job("* * 29 2 * true").next_value(end_of_year)
        datetime.datetime(2016, 2, 29, 0, 0)
        >>> Job("* * 29 2 * true").next_value(
        ...     datetime.datetime(2196, 2, 29, 23, 59))
        datetime.datetime(2204, 2, 29, 0, 0)
        """
        c_min, c_hour, c_dom, c_month, c_dow, c_year = (
            dt.minute, dt.hour, dt.day, dt.month, dt.isoweekday(), dt.year)

        def try_to(next_min, next_hour, next_dom,
                   next_month, next_year, specifics):
            for i in range(1000):
                (min_carry, next_min) = self.mins.next_value(c_min)
                (hour_carry, next_hour) = self.hours.next_value(c_hour,
                                                                min_carry)
                dom_carry, next_dom = specifics(hour_carry)
                (month_carry, next_month) = self.months.next_value(
                    c_month, dom_carry)
                next_year += month_carry
                try:
                    return datetime.datetime(
                        next_year, next_month, next_dom, next_hour, next_min)
                except ValueError:
                    continue
            if i == 999:
                raise ValueError("Couldn't find a valid time for the cron job")

        def specifics_dom(next_dom):
            def specifics_dom(hour_carry):
                nonlocal next_dom
                (dom_carry, next_dom) = self.doms.next_value(
                    next_dom, hour_carry)
                return dom_carry, next_dom
            return specifics_dom

        def specifics_dow(next_dow, next_date):
            def specifics_dow(hour_carry):
                nonlocal next_dow, next_date
                current_dow = next_dow
                (dow_carry, next_dow) = self.dows.next_value(
                    next_dow, hour_carry)
                current_date = next_date
                next_date += datetime.timedelta(
                    days=next_dow-current_dow, weeks=dow_carry)
                return next_date.month - current_date.month, next_date.day
            return specifics_dow

        dom_next_date = try_to(
            c_min, c_hour, c_dom, c_month, c_year, specifics_dom(c_dom))
        dow_next_date = try_to(
            c_min, c_hour, c_dom, c_month, c_year, specifics_dow(
                c_dow, datetime.date(c_year, c_month, c_dom)))
        if self.dow_specified and self.dom_specified:
            return min(dom_next_date, dow_next_date)
        elif self.dow_specified and not self.dom_specified:
            return dow_next_date
        else:
            return dom_next_date
        return min(dom_next_date, dow_next_date)


class Set:

    """
    Represents a set of ranges in one particular field of one particular
    job.
    >>> Set("1-5/4,34-57,59,*/30", Job.MINUTE_RANGE).ranges
    (1-5/4, 34-57/1, 59-59/1, 0-59/30)
    """

    def __init__(self, field, star_range):
        self.ranges = tuple(Range(r, star_range) for r in field.split(","))

    def __repr__(self):
        return ','.join(str(r) for r in self.ranges)

    def next_value(self, current, carry=True):
        """
        Finds the next occurring time for a set of ranges. This should
        be the first of the next_values of all of the ranges in the set.
        >>> Set("1-5/4,34-57,59,*/30", Job.MINUTE_RANGE).next_value(23)
        (False, 30)
        >>> Set("1-4,3-7", Job.MINUTE_RANGE).next_value(8)
        (True, 1)
        """
        return min(r.next_value(current, carry) for r in self.ranges)


class Range:

    """
    Represents a range of times, plus an optional step value.
    >>> Range("1-4/3", Job.MINUTE_RANGE)
    1-4/3
    >>> Range("0-59", Job.MINUTE_RANGE)
    0-59/1
    >>> Range("4", Job.MINUTE_RANGE)
    4-4/1
    >>> Range("*/5", Job.MINUTE_RANGE)
    0-59/5
    >>> Range("*", Job.DOW_RANGE)
    1-7/1
    >>> Range("", Job.MINUTE_RANGE)
    Traceback (most recent call last):
    ...
    CronSyntaxError: Invalid Field
    >>> Range("1-4/3/5", Job.MINUTE_RANGE)
    Traceback (most recent call last):
    ...
    CronSyntaxError: Invalid Field
    >>> Range("/5", Job.MINUTE_RANGE)
    Traceback (most recent call last):
    ...
    CronSyntaxError: Invalid Field
    >>> Range("", Job.MINUTE_RANGE)
    Traceback (most recent call last):
    ...
    CronSyntaxError: Invalid Field

    >>> Range("1-4-3", Job.MINUTE_RANGE)
    Traceback (most recent call last):
    ...
    CronSyntaxError: Invalid Field
    """

    def __init__(self, range, star_range):
        error_info = ("<string>", -1, -1, range)
        (self.star_min, self.star_max) = star_range
        range = range.replace("*", "{}-{}".format(*star_range))
        range_step = range.split('/')
        if len(range_step) == 1:
            self.step = 1
        elif len(range_step) == 2:
            try:
                self.step = int(range_step[1])
                if self.step < 0:
                    raise CronSyntaxError("Invalid Field",
                                          error_info)
            except IndexError or ValueError:
                raise CronSyntaxError("Invalid Field",
                                      error_info) from None
        else:
            raise CronSyntaxError("Invalid Field", error_info)
        raw_range = range_step[0].split('-')
        try:
            if len(raw_range) == 1:
                self.min = int(raw_range[0])
                self.max = int(raw_range[0])
            elif len(raw_range) == 2:
                self.min, self.max = map(int, raw_range)
                if self.min > self.max:
                    raise CronSyntaxError("Invalid Field", error_info)
            else:
                raise CronSyntaxError("Invalid Field", error_info)
        except ValueError:
            raise CronSyntaxError("Invalid Field", error_info) from None

    def __repr__(self):
        return '{}-{}/{}'.format(self.min, self.max, self.step)

    def next_value(self, current, carry=True):
        """
        Returns the following value that this particular range will be
        triggered on, as well as a bool indicating if the range had to
        wrap around to reach this value.
        >>> Range("*", Job.MINUTE_RANGE).next_value(4)
        (False, 5)
        >>> Range("*", Job.MINUTE_RANGE).next_value(59)
        (True, 0)
        >>> Range("*", Job.HOUR_RANGE).next_value(23, carry=False)
        (False, 23)
        >>> Range("*", Job.HOUR_RANGE).next_value(23, carry=True)
        (True, 0)
        >>> Range("*", Job.HOUR_RANGE).next_value(24, carry=True)
        (True, 0)
        >>> Range("*", Job.HOUR_RANGE).next_value(0, carry=False)
        (False, 0)
        >>> Range("5-20/11", Job.MINUTE_RANGE).next_value(17)
        (True, 5)
        >>> Range("5-20/11", Job.MINUTE_RANGE).next_value(11)
        (False, 16)
        >>> Range("59-60/29", Job.MINUTE_RANGE).next_value(3)
        (False, 59)
        >>> Range("29-60/29", Job.MINUTE_RANGE).next_value(3)
        (False, 29)
        """
        distance = ceil((current + carry - self.min)/self.step)
        next = self.min + self.step*distance
        if current+carry < self.min:
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
        ...     v = Range("{}-{}/{}".format(min, randint(min, 59),
        ...             randint(1, 59)), Job.MINUTE_RANGE)
        ...     s = randint(0, 59)
        ...     c = randint(0, 1)
        ...     assert v.next_value(s, c) == v.validate(s, c), (
        ...             v, v.next_value(s, c), v.validate(s, c))
        """
        min = self.min
        for i in range(100):
            if current+carry < self.min:
                return (False, self.min)
            elif min > self.max:
                return (True, self.min)
            elif min >= current+carry:
                return (False, min)
            min += self.step
        assert False, "Why isn't min bigger than self.max or current+1 yet?"


class CronSyntaxError(SyntaxError):
    pass

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
