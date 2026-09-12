"""Regressions for database regex validation in API and web filters."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, DatabaseError, OperationalError, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import django_filters
from rest_framework.test import APIClient

from nautobot.core.filters import BaseFilterSet
from nautobot.core.utils.regex import MYSQL_REGEX_PATTERN_ERRORS, validate_regex
from nautobot.dcim.filters import InterfaceFilterSet
from nautobot.ipam.filters import NamespaceFilterSet
from nautobot.ipam.models import Namespace


class RegexFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="regex-filter-tests", is_superuser=True)
        cls.namespace = Namespace.objects.create(name="regex-target")
        cls.other_namespace = Namespace.objects.create(name="REGEX-OTHER")

    def setUp(self):
        self.api_client = APIClient(HTTP_HOST="nautobot.example.com")
        self.api_client.force_authenticate(self.user)

    def test_invalid_patterns_return_api_field_errors(self):
        for endpoint, field in (("ipam-api:namespace-list", "name"), ("dcim-api:interface-list", "mac_address")):
            for suffix in ("re", "nre", "ire", "nire"):
                for pattern in ("[", "(", "\\", "[z-a]", "a\x00b"):
                    with self.subTest(endpoint=endpoint, suffix=suffix, pattern=pattern):
                        key = f"{field}__{suffix}"
                        response = self.api_client.get(reverse(endpoint), {key: ["valid", pattern]})
                        self.assertEqual(response.status_code, 400, response.content)
                        self.assertIn(key, response.data)
                        self.assertTrue(Namespace.objects.filter(pk=self.namespace.pk).exists())

    def test_valid_regex_matching_and_negation(self):
        queryset = Namespace.objects.filter(pk__in=[self.namespace.pk, self.other_namespace.pk])
        for suffix, expected in (
            ("re", {self.namespace.pk}),
            ("nre", {self.other_namespace.pk}),
            ("ire", {self.namespace.pk, self.other_namespace.pk}),
            ("nire", set()),
        ):
            with self.subTest(suffix=suffix):
                filterset = NamespaceFilterSet({f"name__{suffix}": ["^regex-"]}, queryset=queryset)
                self.assertTrue(filterset.is_valid(), filterset.errors)
                self.assertEqual(set(filterset.qs.values_list("pk", flat=True)), expected)

    def test_database_specific_patterns_are_preserved(self):
        pattern = r"\mregex\M" if connection.vendor == "postgresql" else r"\p{Lower}+"
        filterset = NamespaceFilterSet({"name__re": [pattern]})
        self.assertTrue(filterset.is_valid(), filterset.errors)
        self.assertIn(self.namespace, filterset.qs)
        self.assertEqual(filterset.form.cleaned_data["name__re"], [pattern])

    def test_invalid_web_filter_displays_error_and_empty_table(self):
        client = Client(HTTP_HOST="nautobot.example.com")
        client.force_login(self.user)
        response = client.get(reverse("ipam:namespace_list"), {"name__re": "["})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertContains(response, "Invalid filters were specified")
        self.assertContains(response, "Enter a valid regular expression for this database.")
        self.assertEqual(len(response.context["table"].rows), 0)

    def test_empty_queryset_still_rejects_invalid_pattern(self):
        filterset = NamespaceFilterSet({"name__re": ["["]}, queryset=Namespace.objects.none())
        self.assertFalse(filterset.is_valid())
        self.assertIn("name__re", filterset.errors)

    def test_explicit_scalar_regex_filter_is_validated(self):
        class ExplicitFilterSet(BaseFilterSet):
            pattern = django_filters.CharFilter(field_name="name", lookup_expr="regex")

            class Meta:
                model = Namespace
                fields = []

        filterset = ExplicitFilterSet({"pattern": "["})
        self.assertFalse(filterset.is_valid())
        self.assertIn("pattern", filterset.errors)

    def test_no_regex_adds_no_validation_queries(self):
        for params in ({}, {"name": ["regex-target"]}, {"name__ic": ["regex"]}, {"name__re": []}):
            with self.subTest(params=params), self.assertNumQueries(0):
                filterset = NamespaceFilterSet(params)
                self.assertTrue(filterset.is_valid(), filterset.errors)

    def test_multiple_patterns_use_one_select_and_validation_is_cached(self):
        filterset = NamespaceFilterSet({"name__re": ["^regex", "OTHER$", "^regex"]})
        with CaptureQueriesContext(connection) as queries:
            self.assertTrue(filterset.is_valid(), filterset.errors)
        selects = [query["sql"] for query in queries if query["sql"].startswith("SELECT")]
        self.assertEqual(len(selects), 1)
        self.assertNotIn("FROM", selects[0])
        with self.assertNumQueries(0):
            self.assertTrue(filterset.is_valid())

    def test_regex_widget_retains_submitted_pattern(self):
        filterset = InterfaceFilterSet({"mac_address__re": ["^00:11:"]})
        self.assertTrue(filterset.is_valid(), filterset.errors)
        rendered = str(filterset.form["mac_address__re"])
        self.assertIn("nautobot-select2-multi-value-char", rendered)
        self.assertIn('value="^00:11:" selected', rendered)

    def test_pattern_is_passed_as_a_sql_parameter(self):
        calls = []

        def capture(execute, sql, params, many, context):
            if sql.startswith("SELECT"):
                calls.append((sql, params))
            return execute(sql, params, many, context)

        pattern = "'; SELECT 1; --"
        with connection.execute_wrapper(capture):
            validate_regex([pattern], using=connection.alias, lookup_expr="regex")
        self.assertEqual(len(calls), 1)
        self.assertNotIn(pattern, calls[0][0])
        self.assertIn(pattern, calls[0][1])

    def test_regex_failure_preserves_outer_transaction(self):
        with transaction.atomic():
            namespace = Namespace.objects.create(name="regex-transaction")
            with self.assertRaises(ValidationError):
                validate_regex(["["], using=connection.alias, lookup_expr="regex")
            self.assertTrue(Namespace.objects.filter(pk=namespace.pk).exists())

    def test_unrelated_database_error_is_not_reclassified(self):
        failure = OperationalError("database unavailable")
        with patch.object(connection, "cursor", side_effect=failure):
            with self.assertRaises(OperationalError) as raised:
                validate_regex(["valid"], using=connection.alias, lookup_expr="regex")
        self.assertIs(raised.exception, failure)

    def test_mysql_adapter_only_translates_pattern_errors(self):
        # Real database tests exercise the probe. Simulate the complete error-code mapping here.
        fake_connection = SimpleNamespace(
            vendor="mysql",
            get_autocommit=lambda: True,
        )
        with (
            patch("nautobot.core.utils.regex.connections", {"mysql_test": fake_connection}),
            patch("nautobot.core.utils.regex.Query") as query,
        ):
            query.return_value.get_compiler.return_value.compile.return_value = ("REGEXP_LIKE(%s, %s, 'c')", ["", "["])
            for code in MYSQL_REGEX_PATTERN_ERRORS | {1139, 2006, 3684, 3686, 3687, 3698, 3699}:
                with self.subTest(code=code):
                    failure = DatabaseError(code, "test error")
                    fake_connection.cursor = Mock(side_effect=failure)
                    expected = ValidationError if code in MYSQL_REGEX_PATTERN_ERRORS else DatabaseError
                    with self.assertRaises(expected):
                        validate_regex(["["], using="mysql_test", lookup_expr="regex")


class RegexAutocommitTests(TransactionTestCase):
    def test_probe_does_not_open_transaction_in_autocommit(self):
        self.assertTrue(connection.get_autocommit())
        with self.assertNumQueries(1):
            validate_regex(["^valid", "pattern$"], using=connection.alias, lookup_expr="regex")
        with self.assertNumQueries(1), self.assertRaises(ValidationError):
            validate_regex(["["], using=connection.alias, lookup_expr="regex")
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            self.assertEqual(cursor.fetchone(), (1,))
