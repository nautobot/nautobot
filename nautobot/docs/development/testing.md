# Testing Nautobot

Best practices for developing and maintaining Nautobot's automated unit/integration test suites.

Unit tests are automated tests written and run to ensure that a section of the Nautobot application (known as the "unit") meets its design and behaves as intended and expected. Most commonly as a developer of or contributor to Nautobot you will be writing unit tests to exercise the code you have written. Unit tests are not meant to test how the application behaves, only the individual blocks of code, therefore use of mock data and phony connections is common in unit test code. As a guiding principle, unit tests should be fast, because they will be executed quite often.

Integration tests are automated tests written and run to ensure that the Nautobot application behaves as expected when being used as it would be in practice. By contrast to unit tests, where individual units of code are being tested, integration tests rely upon the server code actually running, and web UI clients or API clients to make real connections to the service to exercise actual workflows, such as navigating to the login page, filling out the username/passwords fields, and clicking the "Log In" button.

Integration testing is much more involved, and builds on top of the foundation laid by unit testing. As a guiding principle, integration tests should be comprehensive, because they are the last mile to asserting that Nautobot does what it is advertised to do. Without integration testing, we have to do it all manually, and that's no fun for anyone!

## Tagging Tests

By Nautobot convention, **unit** tests must be [tagged](https://docs.djangoproject.com/en/stable/topics/testing/tools/#tagging-tests) with `unit`. The base test case class `nautobot.utilities.testing.TestCase` has this tag, therefore any test cases inheriting from that class do not need to be explicitly tagged. All existing view and API test cases in the Nautobot test suite inherit from this class.

By Nautobot convention, **integration** tests must be [tagged](https://docs.djangoproject.com/en/stable/topics/testing/tools/#tagging-tests) with `integration`. The base test case class `nautobot.utilities.testing.integration.SeleniumTestCase` has this tag, therefore any test cases inheriting from that class do not need to be explicitly tagged. All existing integration test cases in the Nautobot test suite inherit from this class.

The `invoke unittest` and `invoke integration-test` commands are intentionally distinct, and the correct tagging of test cases is essential to enforcing the division between these two test categories. We never want to risk running the unit tests and integration tests at the same time. The isolation from each other is critical to a clean and manageable continuous development cycle.

## Base Classes and Code Location

| Test Type   | Base Class                                                | Code Location                              |
| ----------- | --------------------------------------------------------- | ------------------------------------------ |
| Unit        | `nautobot.utilities.testing.TestCase`                     | `nautobot/APP/tests/test_*.py`             |
| Integration | `nautobot.utilities.testing.integration.SeleniumTestCase` | `nautobot/APP/tests/integration/test_*.py` |

- New unit tests **must always** inherit from `nautobot.utilities.testing.TestCase`. Do not use `django.test.TestCase`.
- New integration tests **must always** inherit from `nautobot.utilities.testing.integration.SeleniumTestCase`. Do not use any other base class for integration tests.

## Factories

+++ 1.5.0

Nautobot uses the [`factory_boy`](https://factoryboy.readthedocs.io/en/stable/) library as a way to generate randomized but plausible database data for use in unit and integration tests, or for convenience in populating a local development instance.

Factories for each Nautobot app's models are defined in the corresponding `nautobot/APPNAME/factory.py` files. Helper classes and functions for certain common patterns are defined in `nautobot/utilities/factory.py`. Factories can be used directly from `nbshell` so long as you have `factory_boy` installed. Examples:

```python
>>> from nautobot.tenancy.factory import TenantFactory, TenantGroupFactory
>>> # Create a single TenantGroup instance
>>> TenantGroupFactory.create()
<TenantGroup: Peterson, Nunez and Miller>
>>> # Create 5 Tenant instances
>>> TenantFactory.create_batch(5)
[<Tenant: Smith-Vance>, <Tenant: Sanchez, Brown and Davis>, <Tenant: Benson and Sons>, <Tenant: Pennington PLC>, <Tenant: Perez and Sons>]
>>> # Create 5 more Tenant instances all with a specified "group" value
>>> TenantFactory.create_batch(5, group=TenantGroup.objects.first())
[<Tenant: Mercado, Wilson and Fuller>, <Tenant: Blackburn-Andrade>, <Tenant: Oliver-Ramirez>, <Tenant: Pugh-Clay>, <Tenant: Norman and Sons>]
```

!!! warning
    `factory_boy` is only a *development* dependency of Nautobot. You cannot use the model factories in a production deployment of Nautobot unless you directly `pip install factory_boy` into such a deployment.

Nautobot's custom [test runner](https://docs.djangoproject.com/en/3.2/topics/testing/advanced/#defining-a-test-runner) class (`nautobot.core.tests.runner.NautobotTestRunner`) makes use of the various factories to pre-populate the test database with data before running any tests. This reduces the need for individual tests to define their own baseline data sets.

!!! info
    Because plugins also commonly use Nautobot's test runner, the base Nautobot `settings.py` currently defaults [`TEST_USE_FACTORIES`](../configuration/optional-settings.md#test_use_factories) to `False` so as to not negatively impact plugin tests that may not be designed to account for the presence of pre-populated test data in the database. This configuration is overridden to `True` in `nautobot/core/tests/nautobot_config.py` for Nautobot's own tests.

## Performance Tests

+++ 1.5.0

### Running Performance Tests

Nautobot uses [`django-slowtests`](https://pypi.org/project/django-slowtests/) to run performance tests. To run performance tests, you need to install the `django-slowtests` package.
Once you install the package, you can do `invoke performance-test` or `invoke unittest --performance-test` to run unit tests with `NautobotPerformanceTestRunner`. The invoke commands will automatically add `--testrunner nautobot.core.tests.runner.NautobotPerformanceTestRunner` to the `coverage run` command and this flag will replace the default `NautobotTestRunner` while retaining all its functionalities with the addition of performance evaluation after test runs.

`NautobotPerformanceTestRunner` which inherits from `DiscoverSlowestTestsRunner` will only be available when `django-slowtests` is installed. The runner measures the time to run unit tests against baselines stored in a designated .yml file (defaults to `nautobot/core/tests/performance_baselines.yml`) in addition to running the unit tests themselves.

!!! warning
    This functionality requires the installation of the [`django-slowtests`](https://pypi.org/project/django-slowtests/) Python package, which is present in Nautobot's own development environment, but is *not* an inherent dependency of the Nautobot package when installed otherwise, such as into a plugin's development environment.

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
    To output the performance evaluation to a file for later use, i.e. as performance baselines for future test runs, do `invoke performance-test --performance-snapshot`. This command will collect the `names` of the test and their `execution_time` and store them in a .yml file default to `report.yml`. Subsequently, the data in that file will have to be manually added to the baseline file set at [`TEST_PERFORMANCE_BASELINE_FILE`](../configuration/optional-settings.md#test_performance_baseline_file) to be used as baselines in performance tests.

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

You can add baselines for your own test to `nautobot/core/tests/performance_baselines.yml` or have your own baseline yaml file for performance testing by specifying a different file path for  `TEST_PERFORMANCE_BASELINE_FILE` in plugin's development/test `nautobot_config.py`, and store the output of `invoke performance-test --performance-snapshot` in that file.
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
    Because plugins also commonly use Nautobot's default test runner `NautobotTestRunner`, in order to use `NautobotPerformanceTestRunner` you need to add `django-slowtests` as a part of your plugin dev dependencies.

## Test Code Style

- Use more specific/feature-rich test assertion methods where available (e.g. `self.assertInHTML(fragment, html)` rather than `self.assertTrue(re.search(fragment, html))` or `assert re.search(fragment, html) is not None`).
- Keep test case scope (especially in unit tests) small. Split test functions into smaller tests where possible; otherwise, use `self.subTest()` to delineate test blocks as appropriate.
