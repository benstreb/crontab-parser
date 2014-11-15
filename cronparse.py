"""
This file parses crontabs in order to manipulate them
>>> from io import StringIO
>>> CronTab(StringIO("#comment\\n  \t\\nVAR=3\\n* * * * * true"))
CronTab(jobs=['* * * * * true'])
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
                self.jobs.append(line)

    def __repr__(self):
        return "CronTab(jobs="+repr(self.jobs)+")"

if __name__ == "__main__":
    import doctest
    doctest.testmod()
