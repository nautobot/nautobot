# Testing Apps

In general apps can be tested like other Django apps. In most cases you'll want to run your automated tests via the `nautobot-server test <app_module>` command or, if using the `coverage` Python library, `coverage run --module nautobot.core.cli test <app_module>`.

## Factories

+++ 1.5.0

The [`TEST_USE_FACTORIES`](../../../user-guide/administration/configuration/optional-settings.md#test_use_factories) setting defaults to `False` when testing apps, primarily for backwards-compatibility reasons. It can prove a useful way of populating a baseline of Nautobot database data for your tests and save you the trouble of creating a large amount of baseline data yourself. We recommend adding [`factory-boy`](https://pypi.org/project/factory-boy/) to your app's development dependencies and settings `TEST_USE_FACTORIES = True` in your app's development/test `nautobot_config.py` to take advantage of this.

## Performance Tests

+++ 1.5.0

## Running Performance Tests

You need to install `django-slowtests` as a part of your app dev dependency to run performance tests. It has a very intuitive way to measure the performance of your own tests for your app  (all you have to do is tag your tests with `performance`) and do `invoke performance-test` to get the time to run your tests with `NautobotPerformanceTestRunner`.

`NautobotPerformanceTestRunner` is used by adding the flag `--testrunner nautobot.core.tests.runner.NautobotPerformanceTestRunner` to the `coverage run` command used for unit tests. This flag will replace the default `NautobotTestRunner` while retaining all its functionalities with the addition of performance evaluation after test
runs.
Checkout [Performance Tests](../../core/testing.md#performance-tests) for more detail.

```python
@tag("performance")
def test_your_app(self)
    pass
...
```

## Gathering Performance Test Baseline Data

If you want to add baselines for your own test to `nautobot/core/tests/performance_baselines.yml` or have your own baseline yaml file for performance testing, specify a different file path for  `TEST_PERFORMANCE_BASELINE_FILE` in app's development/test `nautobot_config.py`, and store the output of `invoke performance-test --performance-snapshot` command in that file. `--performance-snapshot` flag will store the results of your performance test to `report.yml` and all you need to do is copy/paste the result to the file set by `TEST_PERFORMANCE_BASELINE_FILE`. Now you have baselines for your own tests!
Example output of `invoke performance-test --performance-snapshot`:

```yaml
tests:
  - name: >-
      test_run_job_with_sensitive_variables_and_requires_approval
      (nautobot.extras.tests.test_views.JobTestCase)
    execution_time: 4.799533
  - name: test_run_missing_schedule (nautobot.extras.tests.test_views.JobTestCase)
    execution_time: 4.367563
  - name: test_run_now_missing_args (nautobot.extras.tests.test_views.JobTestCase)
    execution_time: 4.363194
  - name: >-
      test_create_object_with_constrained_permission
      (nautobot.extras.tests.test_views.GraphQLQueriesTestCase)
    execution_time: 3.474244
  - name: >-
      test_run_now_constrained_permissions
      (nautobot.extras.tests.test_views.JobTestCase)
    execution_time: 2.727531
```

We recommend adding [`django-slowtests`](https://pypi.org/project/django-slowtests/) to your app's development dependencies to leverage this functionality to build better performing apps.
