"""
This file parses crontabs in order to manipulate them
>>> from io import StringIO
>>> CronTab(StringIO("#comment\\n  \t\\nVAR=3\\n* * * * * true"))
CronTab(jobs=[CronJob('* * * * * true')])
"""

import re


class CronTab:

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
        return "CronTab(jobs={})".format(repr(self.jobs))


class CronJob:

    def __init__(self, line):
        self.times = line

    def __repr__(self):
        return "CronJob('{}')".format(self.times)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
