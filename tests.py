import unittest
import doctest
import random
from os import urandom

from parser import CronSyntaxError, parse_range, parse_set, parse_job
from crontab import Range, Set, Job, Bounds


class TestParsing(unittest.TestCase):

    def test_doctests(self):
        import parser
        doctest.testmod(parser, optionflags=doctest.ELLIPSIS)

    def test_parse_job(self):
        B = Bounds
        self.assertEqual(Job((B.minute.range_set(), B.hour.range_set(),
                              B.dom.range_set(), B.month.range_set(),
                              B.dow.range_set()), "yes"),
                         parse_job("* * * * * yes"))

    def test_parse_set(self):
        self.assertEqual(
            Set((Range(1, 5, 4), Range(34, 57),
                 Range(59, 59), Range(0, 59, 30))),
            parse_set("1-5/4,34-57,59,*/30", Bounds.minute))

    def test_parse_range(self):
        equal = self.assertEqual
        equal(Range(1, 4, 3), parse_range("1-4/3", Bounds.minute))
        equal(Range(0, 59, 1), parse_range("0-59", Bounds.minute))
        equal(Range(4, 4, 1), parse_range("4", Bounds.minute))
        equal(Range(0, 59, 5), parse_range("*/5", Bounds.minute))
        equal(Range(1, 7, 1), parse_range("*", Bounds.dow))
        raises = self.assertRaises
        raises(CronSyntaxError, parse_range, "", Bounds.minute)
        raises(CronSyntaxError, parse_range, "1-4/3/5", Bounds.minute)
        raises(CronSyntaxError, parse_range, "/5", Bounds.minute)
        raises(CronSyntaxError, parse_range, "", Bounds.minute)
        raises(CronSyntaxError, parse_range, "1-4-3", Bounds.minute)


class TestCrontab(unittest.TestCase):

    def test_Range_init(self):
        r = Range(1, 59, 2)
        self.assertEqual(r.min, 1)
        self.assertEqual(r.max, 59)
        self.assertEqual(r.step, 2)

    def test_Range_next_value(self):
        equal = self.assertEqual
        all_minutes = Bounds.minute.range()
        equal(all_minutes.next_value(4), (False, 5))
        equal(all_minutes.next_value(59), (True, 0))
        all_hours = Bounds.hour.range()
        equal(all_hours.next_value(23, carry=False), (False, 23))
        equal(all_hours.next_value(23, carry=True), (True, 0))
        equal(all_hours.next_value(24, carry=True), (True, 0))
        equal(all_hours.next_value(0, carry=False), (False, 0))
        equal(Range(5, 20, 11).next_value(17), (True, 5))
        equal(Range(5, 20, 11).next_value(11), (False, 16))
        equal(Range(59, 60, 29).next_value(3), (False, 59))
        equal(Range(29, 60, 29).next_value(3), (False, 29))

    def test_fuzz_Range_next_value(self):
        def validate(r, current, carry):
            if current+carry < r.min:
                return (False, r.min)
            for i in range(r.min, r.max+1, r.step):
                if i >= current+carry:
                    return (False, i)
            return (True, r.min)

        seed = urandom(10)
        random.seed(seed)
        for i in range(1000):
            range_min = min(int(random.expovariate(1/20)), 59)
            v = Range(range_min, random.randint(range_min, 59),
                      min(int(random.expovariate(1/10))+1, 59))
            s = random.randint(0, 59)
            c = random.randint(0, 1)
            self.assertEqual(v.next_value(s, c), validate(v, s, c),
                             "To reproduce, the seed is {}".format(seed))