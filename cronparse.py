"""
This file parses crontabs in order to manipulate them
>>> from io import StringIO
>>> CronTab(StringIO("#comment\\n  \t\\nVAR=3\\n* * * * * true"))
<__main__.CronTab object at 0x...>
"""

import re


class CronTab:

    """
    Parses a CronTab looking for jobs. We only care about jobs for this
    task, so we're ignoring environment variables as well as comments and
    blank lines.
    >>> from io import StringIO
    >>> CronTab(StringIO("* * * * * true")).jobs
    [<__main__.CronJob object at 0x...>]
    """

    def __init__(self, file):
        self.jobs = []
        for line in file:
            line = line.strip()
            if (len(line) == 0 or line.startswith("#") or
                    re.match("\w+\s*=", line)):
                continue
            else:
                self.jobs.append(CronJob(line))


class CronJob:

    """
    Represents a CronJob. This handles parsing of the job to get timing
    information, as well as determining when the job will be run next.
    >>> CronJob("* * * * * true").times
    (*, *, *, *, *)
    >>> CronJob("* * * * * true").job
    'true'
    >>> CronJob("* * * * * echo test").job
    'echo test'
    """

    STAR_RANGES = ("0-59", "0-23", "1-31", "1-12", "1-7")

    def __init__(self, line):
        line = line.split(maxsplit=5)
        self.times = tuple(CronSet(f, r) for f, r in
                           zip(line, CronJob.STAR_RANGES))
        self.job = line[5]


class CronSet:

    """
    Represents a set of ranges in one particular field of one particular
    job.
    >>> CronSet("1-5/4,34-57,59,*/30", "0-59").ranges
    ('1-5/4', '34-57', '59', '*/30')
    """

    def __init__(self, field, star_range):
        self.ranges = tuple(str(r) for r in field.split(","))

    def __repr__(self):
        return ','.join(self.ranges)

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
