from math import ceil

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


class Range:

    """
    Represents a range of times, plus an optional step value.
    """

    def __init__(self, min, max, step):
        self.min = min
        self.max = max
        self.step = step

    def __repr__(self):
        return '{}-{}/{}'.format(self.min, self.max, self.step)

    def next_value(self, current, carry=True):
        """
        Returns the following value that this particular range will be
        triggered on, as well as a bool indicating if the range had to
        wrap around to reach this value.
        >>> all_minutes = MINUTE_RANGE + (1,)
        >>> Range(*all_minutes).next_value(4)
        (False, 5)
        >>> Range(*all_minutes).next_value(59)
        (True, 0)
        >>> all_hours = HOUR_RANGE + (1,)
        >>> Range(*all_hours).next_value(23, carry=False)
        (False, 23)
        >>> Range(*all_hours).next_value(23, carry=True)
        (True, 0)
        >>> Range(*all_hours).next_value(24, carry=True)
        (True, 0)
        >>> Range(*all_hours).next_value(0, carry=False)
        (False, 0)
        >>> Range(5, 20, 11).next_value(17)
        (True, 5)
        >>> Range(5, 20, 11).next_value(11)
        (False, 16)
        >>> Range(59, 60, 29).next_value(3)
        (False, 59)
        >>> Range(29, 60, 29).next_value(3)
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
        ...     v = Range(min, randint(min, 59),
        ...             randint(1, 59))
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

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
