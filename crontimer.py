#!/usr/bin/python3

"""
This file parses Crontabs in order to manipulate them
>>> from io import StringIO
>>> crontab = Crontab(StringIO("#comment\\n  \t\\nVAR=3\\n* * 1 * * true"))
>>> tuple(crontab.next_runs(now=datetime.datetime(2014, 11, 15, 17, 4)))[0]
('true', datetime.datetime(2014, 12, 1, 0, 0))
"""

import argparse
import datetime

import parser


class Crontab:

    """
    Parses a crontab looking for jobs. We only care about jobs for this
    task, so we're ignoring environment variables as well as comments and
    blank lines.
    >>> from io import StringIO
    >>> Crontab(StringIO("* * * * * true")).jobs
    [<crontab.Job object at 0x...>]
    """

    def __init__(self, file):
        self.jobs = parser.parse_crontab(file)

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
