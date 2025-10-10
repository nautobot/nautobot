# Testing Nautobot

Best practices for developing and maintaining Nautobot's automated test suites.

**Unit tests** are automated tests written and run to ensure that a section of the Nautobot application (known as the "unit") meets its design and behaves as intended and expected. Most commonly as a developer of or contributor to Nautobot you will be writing unit tests to exercise the code you have written. Unit tests are not meant to test how the application behaves, only the individual blocks of code, therefore use of mock data and phony connections is common in unit test code. As a guiding principle, unit tests should be fast, because they will be executed quite often.

**Integration tests** are automated tests written and run to ensure that the Nautobot application behaves as expected when being used as it would be in practice. By contrast to unit tests, where individual units of code are being tested, integration tests rely upon the server code actually running, and web UI clients or API clients to make real connections to the service to exercise actual workflows, such as navigating to the login page, filling out the username/passwords fields, and clicking the "Log In" button.

Integration testing is much more involved, and builds on top of the foundation laid by unit testing. As a guiding principle, integration tests should be comprehensive, because they are the last mile to asserting that Nautobot does what it is advertised to do. Without integration testing, we have to do it all manually, and that's no fun for anyone!

**Migration tests** are automated tests written and run to ensure that Nautobot database migrations (primarily "data" migrations in particular, as opposed to "schema" migrations) correctly handle various data scenarios. These are "before/after" tests that bring the database to a particular historical state, populate data into this database state, then run the database migrations (simulating an in-place update of Nautobot) and verify that the final state of the database is as expected.

## Tagging Tests

By Nautobot convention, **unit** tests must be [tagged](https://docs.djangoproject.com/en/stable/topics/testing/tools/#tagging-tests) with `unit`. The base test case class `nautobot.core.testing.TestCase` has this tag, therefore any test cases inheriting from that class do not need to be explicitly tagged. All existing view and API test cases in the Nautobot test suite inherit from this class.

By Nautobot convention, **integration** tests must be [tagged](https://docs.djangoproject.com/en/stable/topics/testing/tools/#tagging-tests) with `integration`. The base test case class `nautobot.core.testing.integration.SeleniumTestCase` has this tag, therefore any test cases inheriting from that class do not need to be explicitly tagged. All existing integration test cases in the Nautobot test suite inherit from this class.

+/- 2.0.0
    The base test classes moved from `nautobot.utilities.testing` to `nautobot.core.testing`.

Nautobot's Python-based **migration** tests are built around the `django-test-migrations` library and its `MigratorTestCase` class, which has the tag `migration_test`, therefore any test cases inheriting from that class do not need to be explicitly tagged.

!!! info "`invoke migration-test`"
    There are also a set of "holistic" migration tests executable by the `invoke migration-test` command; these "tests" consist of nothing more than historical SQL dumps (in the `development/datasets/` directory) of a fully populated database state that can be used to populate an empty database before running a `nautobot-server migrate` command and confirming that it raises no errors. This sort of test is fairly crude; in most cases writing a specific `MigratorTestCase` subclass is to be preferred.

Test cases that depend on the presence of the `example_app` example Nautobot App to function properly must be tagged with the tag `example_app`. Similarly those that depend on the `example_app_with_view_override` must be tagged accordingly as well.

!!! tip "Running tests without the example Apps"
    Because in some cases the presence of the example App(s) can cause side effects in the function of Nautobot itself, an alternate Nautobot test config file is provided that omits these Apps. Running `invoke tests --config-file nautobot/core/tests/nautobot_config_without_example_apps.py` will use this alternate config file, and will additionally automatically skip over the tests that are tagged `example_app` and/or `example_app_with_view_override` since those would be expected to fail in the absence of the example Apps. This can be a useful way to run the majority of the test suite against a "clean" Nautobot installation if interference from the example Apps is a potential concern.

## Base Classes and Code Location

| Test Type   | Base Class                                                      | Code Location                              | Test Execution |
| ----------- | --------------------------------------------------------------- | ------------------------------------------ | ----------------------------------- |
| Unit        | `nautobot.core.testing.TestCase` or subclass (see below)        | `nautobot/APP/tests/test_*.py`             | `invoke tests`                      |
| Integration | `nautobot.core.testing.integration.SeleniumTestCase`            | `nautobot/APP/tests/integration/test_*.py` | `invoke tests --tag integration`    |
| Migration   | `django_test_migrations.contrib.unittest_case.MigratorTestCase` | `nautobot/APP/tests/migration/test_*.py`   | `invoke tests --tag migration_test` |

- New unit tests **must always** inherit from `nautobot.core.testing.TestCase` or one of its subclasses. Do not use `django.test.TestCase` or `unittest.TestCase`.
    - API view test cases should generally inherit from one or more of the classes in `nautobot.core.testing.api.APIViewTestCases`.
    - Filterset test cases should generally inherit from `nautobot.core.testing.filters.FilterTestCases.FilterTestCase`.
    - Form test cases should generally inherit from `nautobot.core.testing.forms.FormTestCases.BaseFormTestCase`.
    - Model test cases should generally inherit from `nautobot.core.testing.models.ModelTestCases.BaseModelTestCase`.
    - View test cases should generally inherit from one or more of the classes in `nautobot.core.testing.views.ViewTestCases`.
- New integration tests **must always** inherit from `nautobot.core.testing.integration.SeleniumTestCase`. Do not use any other base class for integration tests.

+/- 2.0.0
    The base test classes moved from `nautobot.utilities.testing` to `nautobot.core.testing`.

- New migration tests **should generally** inherit from `django_test_migrations.contrib.unittest_case.MigratorTestCase`; if any other base class is used, you **must** explicitly tag it with the `migration_test` tag.

## Generic Filter Tests

+++ 2.0.0

Nautobot provides a set of generic tests for testing the behavior of FilterSets. These tests are located in [`nautobot.core.testing.filters.FilterTestCase`](../../code-reference/nautobot/apps/testing.md#nautobot.apps.testing.FilterTestCases.FilterTestCase) and can be used to test some common filters in Nautobot.

### Generic Boolean Filter Tests

When using `FilterTestCase`, all filters that are instances of `nautobot.core.filters.RelatedMembershipBooleanFilter` that are not using a custom filter method will be tested to verify that the filter returns the same results as the model's queryset. `RelatedMembershipBooleanFilter` filters will be tested for both `True` and `False` values.

### Generic Multiple Choice Filter Tests

A `generic_filter_tests` attribute with a list of filters can be defined on the test class to run generic tests against multiple choice filters. The `generic_filter_tests` attribute should be in the following format:

```python
generic_filter_tests = (
    # use a single item when the filter name matches the model field name
    ["model_field"],
    # use [filter_name, field_name] when the filter name does not match the model field name
    ["related_object_filter", "related_object__name"],
    # the field name is passed as a kwarg to the `queryset.filter` method, so the dunder syntax can be used to make nested queries
    ["related_object_filter", "related_object__id"],
)
```

### Tags Filter Test

If the model being tested is a `PrimaryModel`, the `tags` filter will be automatically tested by passing at least two values to the filter and verifying that the result matches the equivalent queryset filter.

## Integration Tests

### Troubleshooting Integration Tests

Because integration tests normally involve interacting with Nautobot through a browser via [Selenium](https://www.selenium.dev/selenium/docs/api/py/index.html) and the [Splinter](https://splinter.readthedocs.io/en/latest/) wrapper library, they can be difficult to troubleshoot directly from the Python code when a failure occurs. A common troubleshooting technique is to add a `breakpoint()` at the appropriate place in the Python test code (i.e., immediately prior to the observed failure). When the breakpoint is hit and the test pauses, you can then use a VNC viewer application (such as macOS's "Screen Sharing" app) to connect to the running Selenium instance (`localhost:15900` if using the Docker development environment; the default password if prompted is simply "`secret`"). This will allow you to interact live with the testing web browser in its current state and can often provide invaluable insight into the nature of any test failure.

## Factories

Nautobot uses the [`factory_boy`](https://factoryboy.readthedocs.io/en/stable/) library as a way to generate randomized but plausible database data for use in unit and integration tests, or for convenience in populating a local development instance.

Factories for each Nautobot app's models are defined in the corresponding `nautobot/APPNAME/factory.py` files. Helper classes and functions for certain common patterns are defined in `nautobot/core/factory.py`. Factories can be used directly from `nautobot-server nbshell` so long as you have `factory_boy` installed. Examples:

```python
>>> from nautobot.tenancy.factory import TenantFactory, TenantGroupFactory
>>> # Create a single TenantGroup instance
>>> TenantGroupFactory.create()
<TenantGroup: Peterson, Nunez and Miller>
>>> # Create 5 Tenant instances
>>> TenantFactory.create_batch(5)
[<Tenant: Smith-Vance>, <Tenant: Sanchez, Brown and Davis>, <Tenant: Benson and Sons>, <Tenant: Pennington PLC>, <Tenant: Perez and Sons>]
>>> # Create 5 more Tenant instances all with a specified "tenant_group" value
>>> TenantFactory.create_batch(5, tenant_group=TenantGroup.objects.first())
[<Tenant: Mercado, Wilson and Fuller>, <Tenant: Blackburn-Andrade>, <Tenant: Oliver-Ramirez>, <Tenant: Pugh-Clay>, <Tenant: Norman and Sons>]
```

!!! warning
    `factory_boy` is only a *development* dependency of Nautobot. You cannot use the model factories in a production deployment of Nautobot unless you directly `pip install factory_boy` into such a deployment.

Nautobot's custom [test runner](https://docs.djangoproject.com/en/3.2/topics/testing/advanced/#defining-a-test-runner) class (`nautobot.core.tests.runner.NautobotTestRunner`) makes use of the various factories to pre-populate the test database with data before running any tests. This reduces the need for individual tests to define their own baseline data sets.

!!! info
    Because Apps also commonly use Nautobot's test runner, the base Nautobot `settings.py` currently defaults [`TEST_USE_FACTORIES`](../../user-guide/administration/configuration/settings.md#test_use_factories) to `False` so as to not negatively impact App tests that may not be designed to account for the presence of pre-populated test data in the database. This configuration is overridden to `True` in `nautobot/core/tests/nautobot_config.py` for Nautobot's own tests.

!!! warning
    Factories should generally **not** be called within test code, i.e. in a `setUp()` or `setUpTestData()` method. This is because factory output is *stateful*, that is to say the output of any given factory call will depend on the history of *all previous factory calls* since the process was started. This means that a call to a factory within a test case will depend on which other test cases have also called factories, and what order they were called in, as well as whether the initial test database population was done via factories or whether they were bypassed by reuse of cached test data (see below).

    In short, we should only have one place in our tests where factories are called, and that's the `generate_test_data` management command. Individual tests should use standard `create()` or `save()` model methods, never factories.

### Factory Caching

To reduce the time taken between multiple test runs, a new argument has been added to the `nautobot-server test` command: `--cache-test-fixtures`. When running tests with `--cache-test-fixtures` for the first time, after the factory data has been generated it will be saved to a `factory_dump.json` file in the `development` directory. On subsequent runs of unit or integration tests, if `--cache-test-fixtures` is again specified (hint: it is included by default when running `invoke tests`), the factory data will be loaded from the file instead of being generated again. This can significantly reduce the time taken to run tests.

+/- 2.2.7 "Hashing of migrations in the factory dump"
    The test runner now calculates a hash of applied database migrations and uses that as a key when creating/locating the factory data file. This serves as a way to avoid inadvertently using cached test data from the wrong branch or wrong set of migrations, and reduces the frequency with which you might need to manually delete the fixture file. For example, the set of migrations present in `develop` might result in a `factory_dump.966e2e1ed4ae5f924d54.json`, while those in `next` might result in `factory_dump.72b71317c5f5c047493e.json` - both files can coexist, and when you switch between branches during development, the correct one will automatically be selected.

+/- 2.3.4 "Factory caching is enabled by default in invoke tasks"
    Factory caching is now enabled by default with the `invoke tests` command. To bypass it, either use the `--no-cache-test-fixtures` argument to `invoke tests`, or manually remove the `development/factory_dump.*.json` cache file(s).

!!! tip
    Although changes to the set of migrations defined will automatically invalidate an existing factory dump, there are two other cases where you will currently need to manually remove the file in order to force regeneration of the factory data:

    1. When the contents of an existing migration file are modified (the hashing implementation currently can't detect this change).
    2. When the definition of a factory is changed or a new factory is added.

## Test Code Style

- Use more specific/feature-rich test assertion methods where available (e.g. `self.assertInHTML(fragment, html)` rather than `self.assertTrue(re.search(fragment, html))` or `assert re.search(fragment, html) is not None`).
- Keep test case scope (especially in unit tests) small. Split test functions into smaller tests where possible; otherwise, use `self.subTest()` to delineate test blocks as appropriate.
