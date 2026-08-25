import datetime

from nautobot.core.formats import (
    reset_time_format_preference,
    set_time_format_preference,
    TIME_FORMAT_12_HOUR,
    TIME_FORMAT_24_HOUR,
)
from nautobot.core.templatetags import time_formats
from nautobot.core.testing import TestCase


class TimeFormatTemplatetagsTest(TestCase):
    def test_preferred_time_milliseconds(self):
        value = datetime.datetime.fromisoformat("2026-02-23 16:54:03.123456")

        token = set_time_format_preference(TIME_FORMAT_12_HOUR)
        try:
            self.assertEqual(time_formats.preferred_time_milliseconds(value), "4:54:03.123 p.m.")
        finally:
            reset_time_format_preference(token)

        token = set_time_format_preference(TIME_FORMAT_24_HOUR)
        try:
            self.assertEqual(time_formats.preferred_time_milliseconds(value), "16:54:03.123")
        finally:
            reset_time_format_preference(token)
