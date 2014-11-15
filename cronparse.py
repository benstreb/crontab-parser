"""
This file parses crontabs in order to manipulate them
>>> from io import StringIO
>>> CronTab(StringIO("VAR=3\\n* * * * * true"))
CronTab
"""


class CronTab:
    def __init__(self, file):
        pass

    def __repr__(self):
        return "CronTab"

if __name__ == "__main__":
    import doctest
    doctest.testmod()
