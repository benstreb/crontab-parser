import unittest
import doctest
import parser
from parser import CronSyntaxError, parse_range, parse_set
from crontab import Range, Set, Job, Bounds


class TestParsing(unittest.TestCase):

    def test_doctests(self):
        doctest.testmod(parser, optionflags=doctest.ELLIPSIS)

    def test_parse_range(self):
        self.assertEqual(Range(1, 4, 3),
                         parse_range("1-4/3", Bounds.minute))
        self.assertEqual(Range(0, 59, 1),
                         parse_range("0-59", Bounds.minute))
        self.assertEqual(Range(4, 4, 1),
                         parse_range("4", Bounds.minute))
        self.assertEqual(Range(0, 59, 5),
                         parse_range("*/5", Bounds.minute))
        self.assertEqual(Range(1, 7, 1),
                         parse_range("*", Bounds.dow))
        self.assertRaises(CronSyntaxError,
                          parse_range, "", Bounds.minute)
        self.assertRaises(CronSyntaxError,
                          parse_range, "1-4/3/5", Bounds.minute)
        self.assertRaises(CronSyntaxError,
                          parse_range, "/5", Bounds.minute)
        self.assertRaises(CronSyntaxError,
                          parse_range, "", Bounds.minute)
        self.assertRaises(CronSyntaxError,
                          parse_range, "1-4-3", Bounds.minute)

    def test_parse_set(self):
        self.assertEqual(
            Set((Range(1, 5, 4), Range(34, 57),
                 Range(59, 59), Range(0, 59, 30))),
            parse_set("1-5/4,34-57,59,*/30", Bounds.minute))
