# Testing Apps

In general apps can be tested like other Django apps. In most cases you'll want to run your automated tests via the `nautobot-server test <app_module>` command or, if using the `coverage` Python library, `coverage run --module nautobot.core.cli test <app_module>`.

## Detecting N+1 Query Patterns

The `AssertNoRepeatedQueries` context manager helps detect N+1 query patterns in your tests. It captures all SQL queries executed within the block, normalizes them by stripping literal values to create structural templates, and fails the test if any template repeats more than the specified threshold.

```python
from nautobot.apps.testing import AssertNoRepeatedQueries

class MyTestCase(TestCase):
    def test_list_view_no_n_plus_one(self):
        with AssertNoRepeatedQueries(self, threshold=10):
            self.client.get(reverse("plugins:my_app:widget_list"))

    def test_api_no_n_plus_one(self):
        with AssertNoRepeatedQueries(self, threshold=5):
            response = self.client.get(reverse("plugins-api:my_app-api:widget-list"), **self.header)
```

**Parameters:**

- `test_case` - A `TestCase` instance (typically `self`).
- `threshold` - Maximum allowed repetitions of any single query template (default: `10`).

The context manager normalizes queries by replacing quoted string literals and `IN (...)` clauses with placeholders, so queries that differ only in their parameter values are counted together. If a violation is detected, the test fails with a message showing the offending query pattern(s), their repetition counts, and the total number of queries.

## Factories

The [`TEST_USE_FACTORIES`](../../../user-guide/administration/configuration/settings.md#test_use_factories) setting defaults to `False` when testing apps, primarily for backwards-compatibility reasons. It can prove a useful way of populating a baseline of Nautobot database data for your tests and save you the trouble of creating a large amount of baseline data yourself. We recommend adding [`factory-boy`](https://pypi.org/project/factory-boy/) to your app's development dependencies and settings `TEST_USE_FACTORIES = True` in your app's development/test `nautobot_config.py` to take advantage of this.
