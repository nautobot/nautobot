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

## Fixtures

Nautobot includes a number of [fixture](https://docs.djangoproject.com/en/stable/topics/testing/tools/#fixture-loading) files that are used in our unit and integration tests. You can also load these fixtures into your development database as an alternative to manually populating all data from scratch. A common approach when writing new tests or updating new tests would be to load the existing fixtures, manually design and execute tests, making any needed additions to the data set along the way, then re-exporting the updated data to a fixture and using that as part of the automated test development.

Fixtures are stored as JSON files in the various `nautobot/APPNAME/fixtures/` directories. You can use the `invoke load-fixture --app APP --filename FIXTURE` command to load a given fixture; for example `invoke load-fixture --app extras --filename status` will populate some Status records defined in `nautobot/extras/fixtures/status.json` into the database.

Conversely, you can create or update a fixture file via the `invoke write-fixture --app APP --filename FIXTURE --model MODEL [--model OTHER_MODEL...]` command, for example `invoke write-fixture --app extras --filename status --model extras.status` to save all defined Status records from the current development database to `nautobot/extras/fixtures/status.json`.

Fixtures should be:

- **small** - a fixture should represent instances of a single model or a small set of related models - don't try to represent the entire database in a single fixture.
- **reusable** - a fixture that's only usable for a single test is not very useful - use fixtures to define data that applies to many different test cases.
- **composable** - fixtures can build upon other fixtures - a "Site and Region" fixture will depend on a "Status" fixture, a "Device" fixture will depend on both of these, etc.

Along the same lines, tests should:

- **use fixtures, not code, for baseline data** - minimize creation of data in `setUp()` and `setUpTestData()`; prefer fixtures for this purpose.
- **use only the fixtures that are required** - loading fixtures takes non-zero time, so don't include it if you don't need it.
- **reuse existing fixtures when possible** - don't create new fixtures if an existing fixture meets needs or can be minimally augmented to do so.

## Test Code Style

- Use more specific/feature-rich test assertion methods where available (e.g. `self.assertInHTML(fragment, html)` rather than `self.assertTrue(re.search(fragment, html))` or `assert re.search(fragment, html) is not None`).
- Keep test case scope (especially in unit tests) small. Split test functions into smaller tests where possible; otherwise, use `self.subTest()` to delineate test blocks as appropriate.
