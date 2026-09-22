"""Tests for complexity cost budget accounting."""

from unittest.mock import patch
import uuid

from django.test import SimpleTestCase
from django_redis import get_redis_connection
import redis.exceptions

from nautobot.core.rate_limiting.budget_helpers import (
    charge_bucket,
    get_rate_limit_bucket_id,
)


class GetRateLimitBucketIdTestCase(SimpleTestCase):
    """Test logic for rate limiting bucket identification."""

    def test_token_is_never_present_in_the_bucket_id(self):
        token_key = "0123456789abcdef0123456789abcdef01234567"  # noqa: S105  # hardcoded-password-string
        user_token = f"Token {token_key}"

        bucket_id = get_rate_limit_bucket_id(user_token)

        self.assertNotIn(token_key, bucket_id)

    def test_distinct_tokens_get_distinct_buckets(self):
        first_bucket_id = get_rate_limit_bucket_id("Token aaaa")
        second_bucket_id = get_rate_limit_bucket_id("Token bbbb")

        self.assertNotEqual(first_bucket_id, second_bucket_id)

    def test_same_token_gets_the_same_bucket(self):
        first_bucket_id = get_rate_limit_bucket_id("Token aaaa")
        second_bucket_id = get_rate_limit_bucket_id("Token aaaa")

        self.assertEqual(first_bucket_id, second_bucket_id)


class ChargeBucketTestCase(SimpleTestCase):
    """Test logic for budget charging."""

    timeout = 10

    def setUp(self):
        super().setUp()
        self.connection = get_redis_connection("default")
        self.bucket_id = f"test:{uuid.uuid4().hex}"
        self.addCleanup(self.connection.delete, self.bucket_id)

    def test_first_charge_reports_the_cost_as_consumed(self):
        consumed_budget, _ = charge_bucket(self.bucket_id, 4, self.timeout)

        self.assertEqual(consumed_budget, 4)

    def test_first_charge_sets_ttl_correctly(self):
        _, remaining_timeout = charge_bucket(self.bucket_id, 4, self.timeout)

        self.assertEqual(remaining_timeout, self.timeout)

    def test_cost_accumulates_across_charges(self):
        charge_bucket(self.bucket_id, 4, self.timeout)
        charge_bucket(self.bucket_id, 7, self.timeout)

        consumed_budget, _ = charge_bucket(self.bucket_id, 3, self.timeout)

        self.assertEqual(consumed_budget, 14)

    def test_bucket_is_given_an_expiry(self):
        charge_bucket(self.bucket_id, 4, self.timeout)

        bucket_ttl = self.connection.ttl(self.bucket_id)

        self.assertEqual(bucket_ttl, self.timeout)

    def test_later_charges_do_not_extend_the_window(self):
        charge_bucket(self.bucket_id, 4, self.timeout)
        self.connection.expire(self.bucket_id, 3)

        _, remaining_timeout = charge_bucket(self.bucket_id, 4, self.timeout)

        self.assertEqual(remaining_timeout, 3)

    def test_buckets_do_not_share_a_budget(self):
        other_bucket_id = f"test:{uuid.uuid4().hex}"
        self.addCleanup(self.connection.delete, other_bucket_id)
        charge_bucket(self.bucket_id, 100, self.timeout)

        consumed_budget, _ = charge_bucket(other_bucket_id, 3, self.timeout)

        self.assertEqual(consumed_budget, 3)

    def test_unreachable_cache_reports_no_consumption(self):
        with patch(
            "nautobot.core.rate_limiting.budget_helpers.get_redis_connection",
            side_effect=redis.exceptions.ConnectionError,
        ):
            consumed_budget, remaining_timeout = charge_bucket(self.bucket_id, 4, self.timeout)

        self.assertIsNone(consumed_budget)
        self.assertIsNone(remaining_timeout)
