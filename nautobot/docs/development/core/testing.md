# Testing Nautobot

Best practices for developing and maintaining Nautobot's automated unit/integration test suites.

Unit tests are automated tests written and run to ensure that a section of the Nautobot application (known as the "unit") meets its design and behaves as intended and expected. Most commonly as a developer of or contributor to Nautobot you will be writing unit tests to exercise the code you have written. Unit tests are not meant to test how the application behaves, only the individual blocks of code, therefore use of mock data and phony connections is common in unit test code. As a guiding principle, unit tests should be fast, because they will be executed quite often.

Integration tests are automated tests written and run to ensure that the Nautobot application behaves as expected when being used as it would be in practice. By contrast to unit tests, where individual units of code are being tested, integration tests rely upon the server code actually running, and web UI clients or API clients to make real connections to the service to exercise actual workflows, such as navigating to the login page, filling out the username/passwords fields, and clicking the "Log In" button.

Integration testing is much more involved, and builds on top of the foundation laid by unit testing. As a guiding principle, integration tests should be comprehensive, because they are the last mile to asserting that Nautobot does what it is advertised to do. Without integration testing, we have to do it all manually, and that's no fun for anyone!

## Tagging Tests

By Nautobot convention, **unit** tests must be [tagged](https://docs.djangoproject.com/en/stable/topics/testing/tools/#tagging-tests) with `unit`. The base test case class `nautobot.core.testing.TestCase` has this tag, therefore any test cases inheriting from that class do not need to be explicitly tagged. All existing view and API test cases in the Nautobot test suite inherit from this class.

By Nautobot convention, **integration** tests must be [tagged](https://docs.djangoproject.com/en/stable/topics/testing/tools/#tagging-tests) with `integration`. The base test case class `nautobot.core.testing.integration.SeleniumTestCase` has this tag, therefore any test cases inheriting from that class do not need to be explicitly tagged. All existing integration test cases in the Nautobot test suite inherit from this class.

+/- 2.0.0
    The base test classes moved from `nautobot.utilities.testing` to `nautobot.core.testing`.

The `invoke unittest` and `invoke integration-test` commands are intentionally distinct, and the correct tagging of test cases is essential to enforcing the division between these two test categories. We never want to risk running the unit tests and integration tests at the same time. The isolation from each other is critical to a clean and manageable continuous development cycle.

## Base Classes and Code Location

| Test Type   | Base Class                                               | Code Location                              |
| ----------- | -------------------------------------------------------- | ------------------------------------------ |
| Unit        | `nautobot.core.testing.TestCase` or subclass (see below) | `nautobot/APP/tests/test_*.py`             |
| Integration | `nautobot.core.testing.integration.SeleniumTestCase`     | `nautobot/APP/tests/integration/test_*.py` |

- New unit tests **must always** inherit from `nautobot.core.testing.TestCase` or one of its subclasses. Do not use `django.test.TestCase`.
    - API view test cases should generally inherit from one or more of the classes in `nautobot.core.testing.api.APIViewTestCases`.
    - Filterset test cases should generally inherit from `nautobot.core.testing.filters.FilterTestCases.FilterTestCase`.
    - Form test cases should generally inherit from `nautobot.core.testing.forms.FormTestCases.BaseFormTestCase`.
    - Model test cases should generally inherit from `nautobot.core.testing.models.ModelTestCases.BaseModelTestCase`.
    - View test cases should generally inherit from one or more of the classes in `nautobot.core.testing.views.ViewTestCases`.
- New integration tests **must always** inherit from `nautobot.core.testing.integration.SeleniumTestCase`. Do not use any other base class for integration tests.

+/- 2.0.0
    The base test classes moved from `nautobot.utilities.testing` to `nautobot.core.testing`.

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

To reduce the time taken between multiple test runs, a new argument has been added to the `nautobot-server test` command: `--cache-test-fixtures`. When running tests with `--cache-test-fixtures` for the first time, after the factory data has been generated it will be saved to a `factory_dump.json` file in the `development` directory. On subsequent runs of unit or integration tests, if `--cache-test-fixtures` is again specified (hint: it is included by default when running `invoke unittest` or `invoke integration-test`), the factory data will be loaded from the file instead of being generated again. This can significantly reduce the time taken to run tests.

+/- 2.2.7 "Hashing of migrations in the factory dump"
    The test runner now calculates a hash of applied database migrations and uses that as a key when creating/locating the factory data file. This serves as a way to avoid inadvertently using cached test data from the wrong branch or wrong set of migrations, and reduces the frequency with which you might need to manually delete the fixture file. For example, the set of migrations present in `develop` might result in a `factory_dump.966e2e1ed4ae5f924d54.json`, while those in `next` might result in `factory_dump.72b71317c5f5c047493e.json` - both files can coexist, and when you switch between branches during development, the correct one will automatically be selected.

+/- 2.3.4 "Factory caching is enabled by default in invoke tasks"
    Factory caching is now enabled by default with the `invoke unittest` and `invoke integration-test` commands. To bypass it, either use the `--no-cache-test-fixtures` argument to `invoke unittest` or `invoke integration-test`, or manually remove the `development/factory_dump.*.json` cache file(s).

!!! tip
    Although changes to the set of migrations defined will automatically invalidate an existing factory dump, there are two other cases where you will currently need to manually remove the file in order to force regeneration of the factory data:

    1. When the contents of an existing migration file are modified (the hashing implementation currently can't detect this change).
    2. When the definition of a factory is changed or a new factory is added.

## Performance Tests

### Running Performance Tests

Nautobot uses [`django-slowtests`](https://pypi.org/project/django-slowtests/) to run performance tests. To run performance tests, you need to install the `django-slowtests` package.
Once you install the package, you can do `invoke performance-test` or `invoke unittest --performance-test` to run unit tests with `NautobotPerformanceTestRunner`. The invoke commands will automatically add `--testrunner nautobot.core.tests.runner.NautobotPerformanceTestRunner` to the `coverage run` command and this flag will replace the default `NautobotTestRunner` while retaining all its functionalities with the addition of performance evaluation after test runs.

`NautobotPerformanceTestRunner` which inherits from `DiscoverSlowestTestsRunner` will only be available when `django-slowtests` is installed. The runner measures the time to run unit tests against baselines stored in a designated .yml file (defaults to `nautobot/core/tests/performance_baselines.yml`) in addition to running the unit tests themselves.

!!! warning
    This functionality requires the installation of the [`django-slowtests`](https://pypi.org/project/django-slowtests/) Python package, which is present in Nautobot's own development environment, but is *not* an inherent dependency of the Nautobot package when installed otherwise, such as into an App's development environment.

!!! info
    `invoke performance-test` is enabled when `django-slowtests` is installed and when called, it will run and evaluate the performance of specific unit tests that are tagged with `performance` i.e. `@tag("performance")`. `invoke unittest --performance-report` and `invoke integration-test --performance-report` will also be enabled and when called, they will generate a performance report for all the tests ran in the terminal.
    If performance baselines for tests are not available:

```no-highlight
175 abnormally slower tests:
Performance baseline for test_account (nautobot.circuits.tests.test_filters.ProviderTestCase) is not available. Test took 0.0758s to run
Performance baseline for test_asn (nautobot.circuits.tests.test_filters.ProviderTestCase) is not available. Test took 0.0427s to run
Performance baseline for test_bulk_create_objects (nautobot.circuits.tests.test_api.CircuitTerminationTest) is not available. Test took 0.2900s to run
Performance baseline for test_bulk_create_objects (nautobot.circuits.tests.test_api.CircuitTest) is not available. Test took 0.2292s to run
Performance baseline for test_bulk_create_objects (nautobot.circuits.tests.test_api.CircuitTypeTest) is not available. Test took 0.1596s to run
Performance baseline for test_bulk_create_objects (nautobot.circuits.tests.test_api.ProviderNetworkTest) is not available. Test took 0.1897s to run
Performance baseline for test_bulk_create_objects (nautobot.circuits.tests.test_api.ProviderTest) is not available. Test took 0.2092s to run
Performance baseline for test_bulk_delete_objects (nautobot.circuits.tests.test_api.CircuitTerminationTest) is not available. Test took 0.1168s to run
Performance baseline for test_bulk_delete_objects (nautobot.circuits.tests.test_api.CircuitTest) is not available. Test took 0.2762s to run
Performance baseline for test_bulk_delete_objects (nautobot.circuits.tests.test_api.CircuitTypeTest) is not available. Test took 0.0663s to run
Performance baseline for test_bulk_delete_objects (nautobot.circuits.tests.test_api.ProviderNetworkTest) is not available. Test took 0.0875s to run
...
```

!!! info
    If performance baselines for tests are available and the time it take to run tests are siginificantly slower than baselines:

```no-highlight
12 abnormally slower tests:
0.9838s test_bulk_import_objects_with_constrained_permission (nautobot.ipam.tests.test_views.VLANTestCase) is significantly slower than the baseline 0.3692s
1.2548s test_create_multiple_objects_with_constrained_permission (nautobot.dcim.tests.test_views.ConsolePortTestCase) is significantly slower than the baseline 0.5385s
1.4289s test_create_multiple_objects_with_constrained_permission (nautobot.dcim.tests.test_views.DeviceBayTestCase) is significantly slower than the baseline 0.5616s
1.1551s test_create_multiple_objects_with_constrained_permission (nautobot.dcim.tests.test_views.InventoryItemTestCase) is significantly slower than the baseline 0.5822s
1.4712s test_create_multiple_objects_with_constrained_permission (nautobot.dcim.tests.test_views.RearPortTestCase) is significantly slower than the baseline 0.5695s
1.5958s test_create_multiple_objects_with_constrained_permission (nautobot.virtualization.tests.test_views.VMInterfaceTestCase) is significantly slower than the baseline 1.0020s
1.0566s test_create_object_with_constrained_permission (nautobot.virtualization.tests.test_views.VirtualMachineTestCase) is significantly slower than the baseline 0.3627s
...
```

!!! info
    To output the performance evaluation to a file for later use, i.e. as performance baselines for future test runs, do `invoke performance-test --performance-snapshot`. This command will collect the `names` of the test and their `execution_time` and store them in a .yml file default to `report.yml`. Subsequently, the data in that file will have to be manually added to the baseline file set at [`TEST_PERFORMANCE_BASELINE_FILE`](../../user-guide/administration/configuration/settings.md#test_performance_baseline_file) to be used as baselines in performance tests.

Example output of `invoke performance-test --performance-snapshot`:

```yaml
- tests:
  - name: test_account (nautobot.circuits.tests.test_filters.ProviderTestCase)
    execution_time: 0.07075
  - name: test_asn (nautobot.circuits.tests.test_filters.ProviderTestCase)
    execution_time: 0.041262
  - name: test_cabled (nautobot.circuits.tests.test_filters.CircuitTerminationTestCase)
    execution_time: 0.268673
  - name: test_cid (nautobot.circuits.tests.test_filters.CircuitTestCase)
    execution_time: 0.116057
  - name: test_circuit_id (nautobot.circuits.tests.test_filters.CircuitTerminationTestCase)
    execution_time: 0.042665
  - name: test_commit_rate (nautobot.circuits.tests.test_filters.CircuitTestCase)
    execution_time: 0.047894
  - name: test_connected (nautobot.circuits.tests.test_filters.CircuitTerminationTestCase)
    execution_time: 0.056196
  - name: test_id (nautobot.circuits.tests.test_filters.CircuitTerminationTestCase)
    execution_time: 0.03598
...
```

### Gathering Performance Test Baseline Data

`TEST_PERFORMANCE_BASELINE_FILE` specifies the file in which performance baselines are stored, defaults to `nautobot/core/tests/performance_baselines.yml`. Currently, only baselines for those unit tests tagged with `performance` are stored.

You can add baselines for your own test to `nautobot/core/tests/performance_baselines.yml` or have your own baseline yaml file for performance testing by specifying a different file path for  `TEST_PERFORMANCE_BASELINE_FILE` in an App's development/test `nautobot_config.py`, and store the output of `invoke performance-test --performance-snapshot` in that file.
`--performance-snapshot` flag will store the results of your performance test to a new `report.yml` and all you need to do is copy/paste the results to the file set by `TEST_PERFORMANCE_BASELINE_FILE`. Now you have baselines for your own tests!

Example output of `invoke performance-test --performance-snapshot`:

```yaml
- tests:
  - name: test_account (nautobot.circuits.tests.test_filters.ProviderTestCase)
    execution_time: 0.07075
  - name: test_asn (nautobot.circuits.tests.test_filters.ProviderTestCase)
    execution_time: 0.041262
  - name: test_cabled (nautobot.circuits.tests.test_filters.CircuitTerminationTestCase)
    execution_time: 0.268673
  - name: test_cid (nautobot.circuits.tests.test_filters.CircuitTestCase)
    execution_time: 0.116057
  - name: test_circuit_id (nautobot.circuits.tests.test_filters.CircuitTerminationTestCase)
...
```

if you decide to run `invoke unittest --performance-test` which will run tests that currently do not have their baselines present in the file, your output could look something like this:

```no-highlight
175 abnormally slower tests:
Performance baseline for test_account (nautobot.circuits.tests.test_filters.ProviderTestCase) is not available. Test took 0.0758s to run
Performance baseline for test_asn (nautobot.circuits.tests.test_filters.ProviderTestCase) is not available. Test took 0.0427s to run
Performance baseline for test_bulk_create_objects (nautobot.circuits.tests.test_api.CircuitTerminationTest) is not available. Test took 0.2900s to run
Performance baseline for test_bulk_create_objects (nautobot.circuits.tests.test_api.CircuitTest) is not available. Test took 0.2292s to run
Performance baseline for test_bulk_create_objects (nautobot.circuits.tests.test_api.CircuitTypeTest) is not available. Test took 0.1596s to run
Performance baseline for test_bulk_create_objects (nautobot.circuits.tests.test_api.ProviderNetworkTest) is not available. Test took 0.1897s to run
Performance baseline for test_bulk_create_objects (nautobot.circuits.tests.test_api.ProviderTest) is not available. Test took 0.2092s to run
Performance baseline for test_bulk_delete_objects (nautobot.circuits.tests.test_api.CircuitTerminationTest) is not available. Test took 0.1168s to run
Performance baseline for test_bulk_delete_objects (nautobot.circuits.tests.test_api.CircuitTest) is not available. Test took 0.2762s to run
Performance baseline for test_bulk_delete_objects (nautobot.circuits.tests.test_api.CircuitTypeTest) is not available. Test took 0.0663s to run
Performance baseline for test_bulk_delete_objects (nautobot.circuits.tests.test_api.ProviderNetworkTest) is not available. Test took 0.0875s to run
...
```

### Caveats

!!! warning
    `django-slowtests` is only a *development* dependency of Nautobot. You cannot run performance tests in a production deployment of Nautobot unless you directly `pip install django-slowtests` into such a deployment.

!!! info
    Because Apps also commonly use Nautobot's default test runner `NautobotTestRunner`, in order to use `NautobotPerformanceTestRunner` you need to add `django-slowtests` as a part of your App dev dependencies.

## Test Code Style

- Use more specific/feature-rich test assertion methods where available (e.g. `self.assertInHTML(fragment, html)` rather than `self.assertTrue(re.search(fragment, html))` or `assert re.search(fragment, html) is not None`).
- Keep test case scope (especially in unit tests) small. Split test functions into smaller tests where possible; otherwise, use `self.subTest()` to delineate test blocks as appropriate.
