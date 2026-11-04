from unittest import skipIf

from django.db import connection, connections

from nautobot.apps.testing import TestCase
from nautobot.core.db.backends.sqlite3.base import DatabaseWrapper
from nautobot.core.db.backends.sqlite3.functions import inet6_ntoa, json_contains
from nautobot.extras.models import Status


class JSONContainsFunctionTest(TestCase):
    """The JSON_CONTAINS function registered on SQLite connections follows PostgreSQL `@>` semantics."""

    def test_containment(self):
        cases = [
            ('{"a": 1, "b": [1, 2]}', '{"a": 1}', 1),
            ('{"a": 1}', '{"a": 2}', 0),
            ('{"a": {"b": [1]}}', '{"a": {"b": [1]}}', 1),
            ("[1, 2, 3]", "[1, 3]", 1),
            ("[1, 2, 3]", "4", 0),
            ('["x", "y"]', '"x"', 1),
            ('[null, "a"]', "[null]", 1),
            ("[true]", "[1]", 0),
            ("[1]", "[1.0]", 1),
        ]
        for target, candidate, expected in cases:
            with self.subTest(target=target, candidate=candidate):
                self.assertEqual(json_contains(target, candidate), expected)

    def test_path_argument(self):
        self.assertEqual(json_contains('{"k": ["a", "b"]}', '["a"]', "$.k"), 1)
        self.assertEqual(json_contains('{"k": ["a", "b"]}', '["a"]', '$."k"'), 1)
        self.assertEqual(json_contains('{"k": ["a", "b"]}', '["a"]', "$.missing"), 0)
        self.assertEqual(json_contains('["a"]', '"a"', "$"), 1)

    def test_null_propagates(self):
        self.assertIsNone(json_contains(None, "1"))
        self.assertIsNone(json_contains("[1]", None))


class INET6NTOAFunctionTest(TestCase):
    def test_renders_packed_addresses(self):
        self.assertEqual(inet6_ntoa(bytes([10, 0, 0, 1])), "10.0.0.1")
        self.assertEqual(inet6_ntoa(bytes(15) + b"\x01"), "::1")
        self.assertIsNone(inet6_ntoa(None))


@skipIf(connection.vendor != "sqlite", "Exercises Nautobot's SQLite backend")
class SQLiteBackendTest(TestCase):
    def test_ordered_querysets_can_be_combined(self):
        """SQLite rejects ORDER BY on compound-query members; the backend's compiler wraps them in subqueries."""
        statuses = Status.objects.order_by("name")
        first, second = statuses[0], statuses[1]
        combined = Status.objects.filter(pk=first.pk).union(Status.objects.filter(pk=second.pk))
        self.assertEqual(set(combined.values_list("pk", flat=True)), {first.pk, second.pk})

        sliced = Status.objects.order_by("name")[:1].union(Status.objects.order_by("-name")[:1])
        self.assertEqual(sliced.count(), 2)

        subquery = Status.objects.filter(
            pk__in=Status.objects.filter(pk=first.pk)
            .order_by("name")
            .union(Status.objects.filter(pk=second.pk).order_by("name"))
            .values("pk")
        )
        self.assertEqual(subquery.count(), 2)

    def test_json_contains_lookup(self):
        status = Status.objects.first()
        status._custom_field_data = {"tags": ["a", "b"], "n": 1}
        status.save()
        self.assertTrue(Status.objects.filter(pk=status.pk, _custom_field_data__tags__contains=["a"]).exists())
        self.assertFalse(Status.objects.filter(pk=status.pk, _custom_field_data__tags__contains=["c"]).exists())
        self.assertTrue(Status.objects.filter(pk=status.pk, _custom_field_data__contains={"n": 1}).exists())

    def test_json_contains_on_key_transforms(self):
        """Key transforms are compiled to JSON text so that scalars keep their JSON type."""
        status = Status.objects.first()
        status._custom_field_data = {"text": "foo", "num": 1, "flag": True, "lst": ["a", "b"], "s123": "123"}
        status.save()
        qs = Status.objects.filter(pk=status.pk)
        matching = [
            {"_custom_field_data__text__contains": "foo"},
            {"_custom_field_data__num__contains": 1},
            {"_custom_field_data__flag__contains": True},
            {"_custom_field_data__lst__contains": ["a"]},
            {"_custom_field_data__s123__contains": "123"},
            {"_custom_field_data__contains": {"lst": ["b"], "num": 1}},
            {"_custom_field_data__lst__contained_by": ["a", "b", "c"]},
        ]
        non_matching = [
            {"_custom_field_data__text__contains": "fo"},
            {"_custom_field_data__flag__contains": 1},
            {"_custom_field_data__lst__contains": ["c"]},
            {"_custom_field_data__s123__contains": 123},
            {"_custom_field_data__missing__contains": "x"},
        ]
        for lookup in matching:
            with self.subTest(lookup=lookup):
                self.assertTrue(qs.filter(**lookup).exists())
        for lookup in non_matching:
            with self.subTest(lookup=lookup):
                self.assertFalse(qs.filter(**lookup).exists())

    def test_connection_defaults(self):
        """The backend applies WAL, a longer lock timeout, and IMMEDIATE transactions unless overridden."""
        self.assertEqual(connection.settings_dict["OPTIONS"]["timeout"], 15)
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            cursor.execute("PRAGMA busy_timeout")
            busy_timeout = cursor.fetchone()[0]
        if not connection.creation.is_in_memory_db(connection.settings_dict["NAME"]):
            self.assertEqual(journal_mode, "wal")
        self.assertEqual(busy_timeout, 15000)

        # The test configuration overrides the transaction mode, so check the computed defaults on fresh wrappers.
        # (Django resolves the transaction mode when it prepares the connection parameters.)
        def transaction_mode_for(**overrides):
            wrapper = DatabaseWrapper(
                {**connection.settings_dict, "OPTIONS": {}, "TEST": {"MIRROR": None}, **overrides}
            )
            wrapper.get_connection_params()
            return wrapper.transaction_mode

        self.assertEqual(transaction_mode_for(), "IMMEDIATE")
        self.assertEqual(transaction_mode_for(OPTIONS={"transaction_mode": "DEFERRED"}), "DEFERRED")
        # A test mirror of another alias must not reserve the write lock that the mirrored alias will need.
        self.assertIsNone(transaction_mode_for(TEST={"MIRROR": "default"}))

    def test_settings_dict_is_shared_with_the_connection_handler(self):
        """Adding option defaults must not replace the dict that new threads build their connections from."""
        self.assertIs(connection.settings_dict, connections.settings[connection.alias])

    def test_query_param_limit_is_raised(self):
        self.assertGreater(connection.features.max_query_params, 999)
