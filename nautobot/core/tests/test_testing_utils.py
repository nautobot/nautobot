from unittest import TestCase as UnitTestTestCase

from nautobot.core.testing import AssertNoRepeatedQueries


class NormalizeSQLTestCase(UnitTestTestCase):
    """Tests for AssertNoRepeatedQueries._normalize_sql."""

    def test_replaces_single_quoted_strings(self):
        sql = "SELECT * FROM mytable WHERE name = 'foo'"
        result = AssertNoRepeatedQueries._normalize_sql(sql)
        self.assertEqual(result, "SELECT * FROM mytable WHERE name = '?'")

    def test_replaces_multiple_quoted_strings(self):
        sql = "SELECT * FROM mytable WHERE name = 'foo' AND status = 'active'"
        result = AssertNoRepeatedQueries._normalize_sql(sql)
        self.assertEqual(result, "SELECT * FROM mytable WHERE name = '?' AND status = '?'")

    def test_replaces_in_clause(self):
        sql = "SELECT * FROM mytable WHERE id IN (1, 2, 3)"
        result = AssertNoRepeatedQueries._normalize_sql(sql)
        self.assertEqual(result, "SELECT * FROM mytable WHERE id IN (?)")

    def test_replaces_in_clause_with_quoted_values(self):
        sql = "SELECT * FROM mytable WHERE name IN ('foo', 'bar', 'baz')"
        result = AssertNoRepeatedQueries._normalize_sql(sql)
        self.assertEqual(result, "SELECT * FROM mytable WHERE name IN (?)")

    def test_no_change_when_no_literals(self):
        sql = "SELECT id, name FROM mytable"
        result = AssertNoRepeatedQueries._normalize_sql(sql)
        self.assertEqual(result, sql)

    def test_empty_string(self):
        self.assertEqual(AssertNoRepeatedQueries._normalize_sql(""), "")

    def test_empty_quoted_string(self):
        sql = "SELECT * FROM mytable WHERE name = ''"
        result = AssertNoRepeatedQueries._normalize_sql(sql)
        self.assertEqual(result, "SELECT * FROM mytable WHERE name = '?'")

    def test_structurally_identical_queries_normalize_to_same_key(self):
        sql1 = "SELECT * FROM mytable WHERE name = 'alice' AND id IN (1, 2)"
        sql2 = "SELECT * FROM mytable WHERE name = 'bob' AND id IN (3, 4, 5)"
        self.assertEqual(
            AssertNoRepeatedQueries._normalize_sql(sql1),
            AssertNoRepeatedQueries._normalize_sql(sql2),
        )

    def test_structurally_different_queries_normalize_differently(self):
        sql1 = "SELECT * FROM mytable WHERE name = 'foo'"
        sql2 = "SELECT * FROM othertable WHERE name = 'foo'"
        self.assertNotEqual(
            AssertNoRepeatedQueries._normalize_sql(sql1),
            AssertNoRepeatedQueries._normalize_sql(sql2),
        )


class AssertNoRepeatedQueriesContextManagerTestCase(UnitTestTestCase):
    """Tests for AssertNoRepeatedQueries context manager behavior (no DB required)."""

    def test_default_threshold_is_10(self):
        ctx = AssertNoRepeatedQueries(self)
        self.assertEqual(ctx.threshold, 10)

    def test_custom_threshold(self):
        ctx = AssertNoRepeatedQueries(self, threshold=5)
        self.assertEqual(ctx.threshold, 5)

    def test_captured_queries_initially_empty(self):
        ctx = AssertNoRepeatedQueries(self)
        self.assertEqual(ctx.captured_queries, [])

    def test_passes_when_queries_within_threshold(self):
        """Simulate queries within threshold using mock."""
        from unittest.mock import MagicMock

        mock_context = MagicMock()
        mock_context.captured_queries = [{"sql": f"SELECT {i} FROM mytable"} for i in range(10)]  # noqa: S608

        ctx = AssertNoRepeatedQueries(self, threshold=10)
        ctx._context = mock_context
        ctx.__enter__()
        ctx.__exit__(None, None, None)
        # No assertion error means it passed

    def test_fails_when_queries_exceed_threshold(self):
        """Simulate repeated queries exceeding threshold."""
        from unittest.mock import MagicMock

        mock_context = MagicMock()
        mock_context.captured_queries = [{"sql": "SELECT * FROM mytable WHERE name = 'test'"}] * 11

        ctx = AssertNoRepeatedQueries(self, threshold=10)
        ctx._context = mock_context

        ctx.__enter__()
        with self.assertRaises(AssertionError) as cm:
            ctx.__exit__(None, None, None)

        self.assertIn("N+1 query pattern", str(cm.exception))
        self.assertIn("threshold of 10", str(cm.exception))

    def test_fails_with_correct_count_in_message(self):
        from unittest.mock import MagicMock

        repeated_query = "SELECT * FROM mytable WHERE id = '1'"
        mock_context = MagicMock()
        mock_context.captured_queries = [{"sql": repeated_query}] * 15

        ctx = AssertNoRepeatedQueries(self, threshold=5)
        ctx._context = mock_context

        ctx.__enter__()
        with self.assertRaises(AssertionError) as cm:
            ctx.__exit__(None, None, None)

        self.assertIn("[15x]", str(cm.exception))
        self.assertIn("Total queries: 15", str(cm.exception))

    def test_normalizes_before_counting(self):
        """Queries with different literal values but same structure should be counted together."""
        from unittest.mock import MagicMock

        mock_context = MagicMock()
        mock_context.captured_queries = [
            {"sql": f"SELECT * FROM mytable WHERE name = '{name}'"}  # noqa: S608
            for name in ["a", "b", "c", "d", "e", "f"]
        ]

        ctx = AssertNoRepeatedQueries(self, threshold=5)
        ctx._context = mock_context

        ctx.__enter__()
        with self.assertRaises(AssertionError) as cm:
            ctx.__exit__(None, None, None)

        # All 6 queries normalize to the same template, exceeding threshold of 5
        self.assertIn("[6x]", str(cm.exception))

    def test_does_not_check_on_exception(self):
        """If an exception occurred inside the block, skip the query check."""
        from unittest.mock import MagicMock

        mock_context = MagicMock()
        # Would normally trigger a failure
        mock_context.captured_queries = [{"sql": "SELECT * FROM mytable"}] * 100

        ctx = AssertNoRepeatedQueries(self, threshold=1)
        ctx._context = mock_context

        ctx.__enter__()
        # Simulate an exception in the block - should NOT raise AssertionError
        result = ctx.__exit__(ValueError, ValueError("test"), None)
        self.assertFalse(result)

    def test_captured_queries_populated_after_exit(self):
        from unittest.mock import MagicMock

        mock_context = MagicMock()
        mock_context.captured_queries = [
            {"sql": "SELECT 1"},
            {"sql": "SELECT 2"},
        ]

        ctx = AssertNoRepeatedQueries(self, threshold=10)
        ctx._context = mock_context

        ctx.__enter__()
        ctx.__exit__(None, None, None)

        self.assertEqual(ctx.captured_queries, ["SELECT 1", "SELECT 2"])

    def test_multiple_violations_reported(self):
        from unittest.mock import MagicMock

        mock_context = MagicMock()
        mock_context.captured_queries = [{"sql": "SELECT * FROM table_a WHERE name = 'x'"}] * 6 + [
            {"sql": "SELECT * FROM table_b WHERE id = '1'"}
        ] * 8

        ctx = AssertNoRepeatedQueries(self, threshold=5)
        ctx._context = mock_context

        ctx.__enter__()
        with self.assertRaises(AssertionError) as cm:
            ctx.__exit__(None, None, None)

        error_msg = str(cm.exception)
        self.assertIn("table_a", error_msg)
        self.assertIn("table_b", error_msg)
        self.assertIn("[6x]", error_msg)
        self.assertIn("[8x]", error_msg)

    def test_violations_sorted_by_count_descending(self):
        from unittest.mock import MagicMock

        mock_context = MagicMock()
        mock_context.captured_queries = [{"sql": "SELECT * FROM low_count"}] * 6 + [
            {"sql": "SELECT * FROM high_count"}
        ] * 20

        ctx = AssertNoRepeatedQueries(self, threshold=5)
        ctx._context = mock_context

        ctx.__enter__()
        with self.assertRaises(AssertionError) as cm:
            ctx.__exit__(None, None, None)

        error_msg = str(cm.exception)
        # high_count (20x) should appear before low_count (6x)
        self.assertLess(error_msg.index("[20x]"), error_msg.index("[6x]"))
