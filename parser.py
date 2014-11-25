import crontab


def parse_job(raw_line):
    """
    Parses a job.
    >>> job = parse_job("* * * * * true")
    >>> (job.mins, job.hours, job.doms, job.months, job.dows)
    (0-59/1, 0-23/1, 1-31/1, 1-12/1, 1-7/1)
    """
    line = raw_line.split(maxsplit=5)
    try:
        times = tuple(parse_set(f, r) for f, r in
                      zip(line, crontab.STAR_RANGES))
        job = crontab.Job(times, line[5])
        job.dom_specified = line[2] != '*'
        job.dow_specified = line[4] != '*'
    except ValueError:
        raise CronSyntaxError("Invalid job", (raw_line, -1, -1, raw_line))
    return job


def parse_set(field, star_range):
    """
    Parses sets of ranges.
    >>> parse_set("1-5/4,34-57,59,*/30", crontab.MINUTE_RANGE).ranges
    (1-5/4, 34-57/1, 59-59/1, 0-59/30)
    """
    ranges = tuple(parse_range(r, star_range) for r in field.split(","))
    return crontab.Set(ranges)


def parse_range(range_step, star_range):
    """
    Parses ranges, which are a range of values plus an optional step.
    >>> parse_range("1-4/3", crontab.MINUTE_RANGE)
    1-4/3
    >>> parse_range("0-59", crontab.MINUTE_RANGE)
    0-59/1
    >>> parse_range("4", crontab.MINUTE_RANGE)
    4-4/1
    >>> parse_range("*/5", crontab.MINUTE_RANGE)
    0-59/5
    >>> parse_range("*", crontab.DOW_RANGE)
    1-7/1
    >>> parse_range("", crontab.MINUTE_RANGE)
    Traceback (most recent call last):
    ...
    CronSyntaxError: Invalid Field
    >>> parse_range("1-4/3/5", crontab.MINUTE_RANGE)
    Traceback (most recent call last):
    ...
    CronSyntaxError: Invalid Field
    >>> parse_range("/5", crontab.MINUTE_RANGE)
    Traceback (most recent call last):
    ...
    CronSyntaxError: Invalid Field
    >>> parse_range("", crontab.MINUTE_RANGE)
    Traceback (most recent call last):
    ...
    CronSyntaxError: Invalid Field

    >>> parse_range("1-4-3", crontab.MINUTE_RANGE)
    Traceback (most recent call last):
    ...
    CronSyntaxError: Invalid Field
    """
    error_info = ("<string>", -1, -1, range_step)
    (star_min, star_max) = star_range
    range_step = range_step.replace("*", "{}-{}".format(*star_range))
    range_step = range_step.split('/')
    if len(range_step) == 1:
        step = 1
    elif len(range_step) == 2:
        try:
            step = int(range_step[1])
            if step < 0:
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
            range_min = int(raw_range[0])
            range_max = int(raw_range[0])
        elif len(raw_range) == 2:
            range_min, range_max = map(int, raw_range)
            if range_min > range_max:
                raise CronSyntaxError("Invalid Field", error_info)
        else:
            raise CronSyntaxError("Invalid Field", error_info)
    except ValueError:
        raise CronSyntaxError("Invalid Field", error_info) from None
    return crontab.Range(range_min, range_max, step)


class CronSyntaxError(SyntaxError):
    pass


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
