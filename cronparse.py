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
        for line in file:
            line = line.strip()
            if (len(line) == 0 or line.startswith("#") or
                    re.match("\w+\s*=", line)):
                continue
            else:
                self.jobs.append(Job(line))


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

    STAR_RANGES = ("0-59", "0-23", "1-31", "1-12", "1-7")

    def __init__(self, line):
        line = line.split(maxsplit=5)
        self.times = tuple(Set(f, r) for f, r in
                           zip(line, Job.STAR_RANGES))
        self.job = line[5]


class Set:

    """
    Represents a set of ranges in one particular field of one particular
    job.
    >>> Set("1-5/4,34-57,59,*/30", "0-59").ranges
    (1-5/4, 34-57/1, 59-59/1, 0-59/30)
    """

    def __init__(self, field, star_range):
        field = field.replace("*", star_range)
        self.ranges = tuple(Range(r) for r in field.split(","))

    def __repr__(self):
        return ','.join(str(r) for r in self.ranges)


class Range:

    """
    Represents a range of times, plus an optional step value.
    >>> Range("1-4/3")
    1-4/3
    >>> Range("0-59")
    0-59/1
    >>> Range("4")
    4-4/1
    """

    def __init__(self, range, step=1):
        range_step = range.split('/')
        if len(range_step) == 1:
            self.step = 1
        else:
            self.step = range_step[1]
        raw_range = range_step[0].split('-')
        if len(raw_range) == 1:
            self.min = raw_range[0]
            self.max = raw_range[0]
        else:
            self.min, self.max = raw_range

    def __repr__(self):
        return '{}-{}/{}'.format(self.min, self.max, self.step)

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
