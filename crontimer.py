#!/bin/python

"""
This file parses Crontabs in order to manipulate them
>>> from io import StringIO
>>> crontab = Crontab(StringIO("#comment\\n  \t\\nVAR=3\\n* * 1 * * true"))
>>> tuple(crontab.next_runs(now=datetime.datetime(2014, 11, 15, 17, 4)))[0]
('true', datetime.datetime(2014, 12, 1, 0, 0))
"""

import argparse
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
        >>> Job("* * 1 * * true").next_value(
        ...     datetime.datetime(2014, 11, 15, 17, 4, 49))
        datetime.datetime(2014, 12, 1, 0, 0)
        >>> Job("* * * * 3 true").next_value(
        ...     datetime.datetime(2014, 11, 15, 17, 4, 49))
        datetime.datetime(2014, 11, 19, 0, 0)
        >>> Job("* * * * 3 true").next_value(
        ...     datetime.datetime(2014, 11, 29, 17, 4, 49))
        datetime.datetime(2014, 12, 3, 0, 0)
        >>> Job("* * * 11 3 true").next_value(
        ...     datetime.datetime(2014, 11, 29, 17, 4, 49))
        datetime.datetime(2015, 11, 4, 0, 0)
        >>> end_of_year = datetime.datetime(2014, 12, 31, 23, 59)
        >>> Job("* * * * * true").next_value(end_of_year)
        datetime.datetime(2015, 1, 1, 0, 0)
        >>> Job("* * 29 2 * true").next_value(end_of_year)
        datetime.datetime(2016, 2, 29, 0, 0)
        >>> Job("* * 29 2 * true").next_value(
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
            delta = dows_to_timedelta(old_dow, dow)
            month_carry, next_month = self.months.next_value(
                month, carry=False)
            if (dt + delta).month == month and next_month == month:
                return dow_carry, dt + delta

            month_carry, next_month = self.months.next_value(month, carry=True)
            dt = dt.replace(year=dt.year+month_carry,
                            month=next_month, day=1)

            tmp_dow = dt.isoweekday() % 7
            _, dow = self.dows.next_value(tmp_dow, carry=False)
            return True, dt + dows_to_timedelta(tmp_dow, dow)

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


def dows_to_timedelta(current, next):
    return datetime.timedelta(
        days=next-current, weeks=1 if next < current else 0)


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
        ...     v = Range("{}-{}/{}".format(min, randint(min, 59),
        ...             randint(1, 59)), Job.MINUTE_RANGE)
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


class CronSyntaxError(SyntaxError):
    pass


def parse_date(date_str):
    """
    Parses a string of the form /mm/dd/yyyy and returns it at as a date
    >>> parse_date("1/31/2014")
    datetime.date(2014, 1, 31)
    >>> parse_date("1/31")
    Traceback (most recent call last):
    ...
    argparse.ArgumentTypeError: date should be of the form mm/dd/yyyy: was 1/31
    """
    try:
        (month, day, year) = map(int, date_str.split('/'))
        return datetime.date(year, month, day)
    except:
        raise argparse.ArgumentTypeError(
            "date should be of the form mm/dd/yyyy: was {}".format(date_str)
            ) from None


def parse_time(time_str):
    """
    Parses a string of the form 1:59 and returns it at as a time
    >>> parse_time("1:59")
    datetime.time(1, 59)
    >>> parse_time("59")
    Traceback (most recent call last):
    ...
    argparse.ArgumentTypeError: time should be of the form hr:min: was 59
    """
    try:
        (hour, min) = map(int, time_str.split(':'))
        return datetime.time(hour, min)
    except:
        raise argparse.ArgumentTypeError(
            "time should be of the form hr:min: was {}".format(time_str))


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
    p = argparse.ArgumentParser(description="""Reads through a crontab and
                                 prints out each job and when it will run""")
    p.add_argument('crontab', help="the location of the crontab to parse")
    p.add_argument('--date', type=parse_date,
                   default=datetime.datetime.now().date(),
                   help="""fake that the program is being run on this date""")
    p.add_argument('--time', type=parse_time,
                   default=datetime.datetime.now().timetz(),
                   help="""fake that the program is being run at this time""")
    args = p.parse_args()
    with open(args.crontab, 'r') as crontab:
        now = datetime.datetime.now()
        dt = datetime.datetime.combine(args.date, args.time)
        for job, time in Crontab(crontab).next_runs(dt):
            print("{}: {}".format(str(time), job))