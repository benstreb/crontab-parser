import unittest
import doctest
import random
from datetime import datetime
from os import urandom

from parser import CronSyntaxError, parse_range, parse_set, parse_job
from crontab import Range, Set, Job, Bounds
from cronparser import Crontab


class TestParsing(unittest.TestCase):

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

    def test_Job_init(self):
        B = Bounds
        Job((B.minute.range_set(),
             B.hour.range_set(),
             B.dom.range_set(),
             B.month.range_set(),
             B.dow.range_set()),
            "yes")

    def test_Job_next_value(self):
        import parser
        parser.parse_job("* * * * * true").next_value(
            datetime(2014, 11, 15, 17, 4, 49))
        datetime(2014, 11, 15, 17, 5)
        parser.parse_job("* * 1 * * true").next_value(
            datetime(2014, 11, 15, 17, 4, 49))
        datetime(2014, 12, 1, 0, 0)
        parser.parse_job("* * * * 3 true").next_value(
            datetime(2014, 11, 15, 17, 4, 49))
        datetime(2014, 11, 19, 0, 0)
        parser.parse_job("* * * * 3 true").next_value(
            datetime(2014, 11, 29, 17, 4, 49))
        datetime(2014, 12, 3, 0, 0)
        parser.parse_job("* * * 11 3 true").next_value(
            datetime(2014, 11, 29, 17, 4, 49))
        datetime(2015, 11, 4, 0, 0)
        end_of_year = datetime(2014, 12, 31, 23, 59)
        parser.parse_job("* * * * * true").next_value(end_of_year)
        datetime(2015, 1, 1, 0, 0)
        parser.parse_job("* * 29 2 * true").next_value(end_of_year)
        datetime(2016, 2, 29, 0, 0)
        parser.parse_job("* * 29 2 * true").next_value(
            datetime(2196, 2, 29, 23, 59))
        datetime(2204, 2, 29, 0, 0)

    def test_Set_init(self):
        ranges = (Range(1, 5, 4), Range(34, 57, 59), Range(59, 59),
                  Range(0, 59, 30))
        s = Set(ranges)
        self.assertEqual(s.ranges, ranges)

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


def load_tests(loader, tests, ignore):
    import parser
    tests.addTests(doctest.DocTestSuite(
        parser, optionflags=doctest.ELLIPSIS))
    import crontab
    tests.addTests(doctest.DocTestSuite(
        crontab, optionflags=doctest.ELLIPSIS))
    import cronparser
    tests.addTests(doctest.DocTestSuite(
        cronparser, optionflags=doctest.ELLIPSIS))
    return tests

if __name__ == "__main__":
    import unittest
    unittest.main(module='tests')
