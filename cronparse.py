"""
This file parses Crontabs in order to manipulate them
>>> from io import StringIO
>>> Crontab(StringIO("#comment\\n  \t\\nVAR=3\\n* * * * * true"))
<__main__.Crontab object at 0x...>
"""

import re


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


class Job:

    """
    Represents a cron job. This handles parsing of the job to get timing
    information, as well as determining when the job will be run next.
    >>> Job("* * * * * true").times
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
        self.times = tuple(Set(f, r) for f, r in
                           zip(line, Job.STAR_RANGES))
        assert(len(self.times) <= 5)
        if len(self.times) < 5:
            raise CronSyntaxError("Invalid job",
                                  (raw_line, -1, -1, raw_line))
        self.job = line[5]


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


class CronSyntaxError(SyntaxError):
    pass

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
