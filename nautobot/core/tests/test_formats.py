import datetime

from django.template.defaultfilters import date, time
from django.test import override_settings

from nautobot.core.testing import TestCase


class FormatsTestCase(TestCase):
    def test_settings_overrides_propagate_to_formats(self):
        with self.subTest("implicit DATE_FORMAT"), override_settings(DATE_FORMAT="Y/m/d"):
            self.assertEqual(date(datetime.date.fromisoformat("2026-02-23")), "2026/02/23")

        with self.subTest("explicit DATE_FORMAT"), override_settings(DATE_FORMAT="Y/m/d"):
            self.assertEqual(date(datetime.date.fromisoformat("2026-02-23"), "DATE_FORMAT"), "2026/02/23")

        with self.subTest("DATETIME_FORMAT"), override_settings(DATETIME_FORMAT="Y/m/d H-i-s"):
            self.assertEqual(
                date(datetime.datetime.fromisoformat("2026-02-23 16:54:03"), "DATETIME_FORMAT"), "2026/02/23 16-54-03"
            )

        with self.subTest("SHORT_DATE_FORMAT"), override_settings(SHORT_DATE_FORMAT="m/d"):
            self.assertEqual(date(datetime.date.fromisoformat("2026-02-23"), "SHORT_DATE_FORMAT"), "02/23")

        with self.subTest("SHORT_DATETIME_FORMAT"), override_settings(SHORT_DATETIME_FORMAT="m/d H-i"):
            self.assertEqual(
                date(datetime.datetime.fromisoformat("2026-02-23 16:54:03"), "SHORT_DATETIME_FORMAT"), "02/23 16-54"
            )

        with self.subTest("TIME_FORMAT"), override_settings(TIME_FORMAT="H/i.s"):
            self.assertEqual(time(datetime.datetime.fromisoformat("2026-02-23 16:54:03"), "TIME_FORMAT"), "16/54.03")
