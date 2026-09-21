"""Tests for fixed-window budget accounting."""

from unittest.mock import patch
import uuid

from django.core.cache import cache
from django.test import SimpleTestCase
import redis.exceptions

from nautobot.core.rate_limiting.budget_helpers import (
    charge_bucket,
    get_current_bucket,
    get_seconds_remaining_in_window,
    get_time_window,
    get_user_rate_limit_bucket_id,
)


class GetUserRateLimitBucketIdTestCase(SimpleTestCase):
    """Test logic for rate limiting bucket management."""

    def test_token_is_never_present_in_the_bucket_id(self):
        token_key = "0123456789abcdef0123456789abcdef01234567"  # noqa: S105  # hardcoded-password-string
        user_token = f"Token {token_key}"

        bucket_id = get_user_rate_limit_bucket_id(user_token, 200)

        self.assertNotIn(token_key, bucket_id)

    def test_distinct_tokens_get_distinct_buckets(self):
        first_bucket_id = get_user_rate_limit_bucket_id("Token aaaa", 200)
        second_bucket_id = get_user_rate_limit_bucket_id("Token bbbb", 200)

        self.assertNotEqual(first_bucket_id, second_bucket_id)

    def test_same_token_in_same_window_gets_same_bucket(self):
        first_bucket_id = get_user_rate_limit_bucket_id("Token aaaa", 200)
        second_bucket_id = get_user_rate_limit_bucket_id("Token aaaa", 200)

        self.assertEqual(first_bucket_id, second_bucket_id)

    def test_same_token_in_different_windows_gets_different_buckets(self):
        first_bucket_id = get_user_rate_limit_bucket_id("Token aaaa", 200)
        second_bucket_id = get_user_rate_limit_bucket_id("Token aaaa", 201)

        self.assertNotEqual(first_bucket_id, second_bucket_id)


class WindowArithmeticTestCase(SimpleTestCase):
    """Test logic for rate limiting window determination."""

    window_duration = 5

    def test_timestamps_within_one_window_share_a_window(self):
        first_window = get_time_window(1000.0, self.window_duration)
        second_window = get_time_window(1004.9, self.window_duration)

        self.assertEqual(first_window, second_window)

    def test_timestamps_across_a_boundary_get_different_windows(self):
        first_window = get_time_window(1004.9, self.window_duration)
        second_window = get_time_window(1005.0, self.window_duration)

        self.assertNotEqual(first_window, second_window)

    def test_seconds_remaining_is_the_full_window_at_a_boundary(self):
        remaining = get_seconds_remaining_in_window(1000.0, self.window_duration)

        self.assertEqual(remaining, self.window_duration)

    def test_seconds_remaining_is_never_zero_at_the_end_of_a_window(self):
        remaining = get_seconds_remaining_in_window(1004.999, self.window_duration)

        self.assertEqual(remaining, 1)


class ChargeBucketTestCase(SimpleTestCase):
    """Test logic for budget charging."""

    counter_timeout = 10

    def setUp(self):
        super().setUp()
        self.bucket_id = f"test:{uuid.uuid4().hex}"
        self.addCleanup(cache.delete, self.bucket_id)

    def test_first_charge_in_a_window_records_the_cost(self):
        charge_bucket(self.bucket_id, 4, self.counter_timeout)

        current_bucket = get_current_bucket(self.bucket_id)

        self.assertEqual(current_bucket, 4)

    def test_cost_accumulates_across_charges(self):
        charge_bucket(self.bucket_id, 4, self.counter_timeout)
        charge_bucket(self.bucket_id, 7, self.counter_timeout)
        charge_bucket(self.bucket_id, 3, self.counter_timeout)

        current_bucket = get_current_bucket(self.bucket_id)

        self.assertEqual(current_bucket, 14)

    def test_counter_is_given_an_expiry(self):
        charge_bucket(self.bucket_id, 4, self.counter_timeout)

        counter_ttl = cache.ttl(self.bucket_id)

        self.assertEqual(counter_ttl, self.counter_timeout)

    def test_buckets_do_not_share_a_budget(self):
        other_bucket_id = f"test:{uuid.uuid4().hex}"
        self.addCleanup(cache.delete, other_bucket_id)
        charge_bucket(self.bucket_id, 100, self.counter_timeout)
        charge_bucket(other_bucket_id, 3, self.counter_timeout)

        current_bucket = get_current_bucket(other_bucket_id)

        self.assertEqual(current_bucket, 3)

    def test_charging_does_not_raise_when_the_counter_is_unreachable(self):
        with patch(
            "nautobot.core.rate_limiting.budget_helpers.cache.incr", side_effect=redis.exceptions.ConnectionError
        ):
            charge_bucket(self.bucket_id, 4, self.counter_timeout)

        self.assertEqual(get_current_bucket(self.bucket_id), 0)


class GetCurrentBucketTestCase(SimpleTestCase):
    """Test logic for bucket retrieval."""

    counter_timeout = 10

    def setUp(self):
        super().setUp()
        self.bucket_id = f"test:{uuid.uuid4().hex}"
        self.addCleanup(cache.delete, self.bucket_id)

    def test_reads_back_what_was_charged(self):
        charge_bucket(self.bucket_id, 4, self.counter_timeout)
        charge_bucket(self.bucket_id, 7, self.counter_timeout)

        current_bucket = get_current_bucket(self.bucket_id)

        self.assertEqual(current_bucket, 11)

    def test_bucket_that_was_never_charged_reads_as_zero(self):
        current_bucket = get_current_bucket(self.bucket_id)

        self.assertEqual(current_bucket, 0)

    def test_returns_none_when_the_counter_is_unreachable(self):
        with patch(
            "nautobot.core.rate_limiting.budget_helpers.cache.get", side_effect=redis.exceptions.ConnectionError
        ):
            current_bucket = get_current_bucket(self.bucket_id)

        self.assertIsNone(current_bucket)
