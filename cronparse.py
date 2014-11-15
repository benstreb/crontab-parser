"""
This file parses crontabs in order to manipulate them
>>> from io import StringIO
>>> CronTab(StringIO("#comment\\n  \t\\nVAR=3\\n* * * * * true"))
CronTab
"""

import re


class CronTab:

    """
    Parses a CronTab looking for jobs. We only care about jobs for this
    task, so we're ignoring environment variables as well as comments and
    blank lines.
    >>> from io import StringIO
    >>> CronTab(StringIO("* * * * * true")).jobs
    [CronJob]
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

    def __repr__(self):
        return "CronTab"


class CronJob:

    """
    Represents a CronJob. This handles parsing of the job to get timing
    information, as well as determining when the job will be run next.
    >>> CronJob("* * * * * true").times
    '* * * * * true'
    """

    def __init__(self, line):
        self.times = line

    def __repr__(self):
        return "CronJob"

if __name__ == "__main__":
    import doctest
    doctest.testmod()
