# Migrating Jobs from Nautobot v1.X to Nautobot v2.0

## Quick Summary of Job Class Changes

* [`self.run(self, data, commit)` must be changed to include all Job variables](#run-method-signature)
* [`self.test_*` and `self.post_run()` methods were removed](#test_-and-post_run-methods)
* [`read_only` no longer changes the behavior of Nautobot core](#read-only-meta-attribute)
* [`self.job_result` should no longer be modified or saved from within a Job](#tracking-job-state)
* [Jobs must be registered in the celery task registry](#job-registration)
* [`self.failed` removed](#tracking-job-state)
* [The job logging methods have been renamed and their signature changed](#job-logging)
* [The `request` property has been changed to a celery request instead of a Django request](#request-property)

## Overview

Some fundamental changes were made to Jobs in Nautobot v2.0. This document outlines the changes that were made and how to migrate your existing Jobs to work in Nautobot v2.0. For more information about the changes made to the Job class and Job model in Nautobot v2.0 see the [Upgrading From Nautobot v1](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#job-changes) documentation.

### Job Package Names

All Jobs are now imported as normal Python packages, instead of virtually imported, which means that Job file code can be shared with other Jobs or Python modules.

#### App Provided Jobs

The package name for Jobs provided by Nautobot Apps has not changed.

#### Jobs in `JOBS_ROOT`

[`JOBS_ROOT`](../../../user-guide/administration/configuration/optional-settings.md#jobs_root) is added to `sys.path` and all modules in that directory will be imported. The package name for Jobs in `JOBS_ROOT` will be `<job_file>`, where `<job_file>` is the name of the Job file without the `.py` extension. If desired, submodules may be used in `JOBS_ROOT` like any normal Python package. For example, a Job class called `AddJob` in `$JOBS_ROOT/my_jobs/math.py` would be imported as `my_jobs.math.AddJob`.

!!! caution
    Take care to avoid naming collisions with existing Python packages when naming Job files in `JOBS_ROOT`.

#### Git Repository Jobs

The package name for Jobs provided by [Git Repositories](../../../user-guide/platform-functionality/gitrepository.md) has changed to `<git_repository_slug>.jobs`, where `<git_repository_slug>` is the slug of the Git Repository as provided by the user when creating the Git Repository object in Nautobot. All jobs provided by Git Repositories must use the `.jobs` submodule of the Git Repository.

!!! important
    As a result of the changes to the way jobs are imported the top-level directory of any Git Repository that provides Jobs must now contain an `__init__.py` file.

### Run Method Signature

The signature of the `run()` method for Jobs must now accept keyword arguments for every [Job variable](../index.md#variables) defined on the Job class. The `run()` method no longer uses the `data` and `commit` arguments used in v1.X.

!!! example
    ```py title="v1.X Job"
    class AddJob(Job):
        a = IntegerVar()
        b = IntegerVar()

        def run(self, data, commit):
            return data["a"] + data["b"]
    ```

    ```py title="v2.0 Job"
    class AddJob(Job):
        a = IntegerVar()
        b = IntegerVar()

        def run(self, a, b):
            return a + b
    ```

### `test_*` and `post_run()` Methods

The `test_*` and `post_run` methods, previously provided for backwards compatibility to NetBox scripts and reports, have been removed. Celery implements `before_start`, `on_success`, `on_retry`, `on_failure`, and `after_return` methods that can be used by Job authors to perform similar functions.

!!! important
    Be sure to call the `super()` method when overloading any of the job's `before_start`, `on_success`, `on_retry`, `on_failure`, or `after_return` methods

### Database Transaction Handling

Jobs no longer run in a single atomic [database transaction](https://docs.djangoproject.com/en/stable/topics/db/transactions/) by default. If a Job needs to run in a database transaction, you can use the `@transaction.atomic` decorator on the `run()` method or wrap parts of your Job code in the `with transaction.atomic()` context manager.

!!! example
    ```py
    from django.db import transaction
    from nautobot.dcim import models
    from nautobot.extras.jobs import Job, ObjectVar

    class UpdateDeviceTypeHeightJob(Job):
        device_type = ObjectVar(model=models.DeviceType)
        u_height = IntegerVar(label="New Height (U)")

        @transaction.atomic
        def run(self, device_type, u_height):
            device_type.u_height = u_height
            device_type.save()
    ```

#### Commit Argument

As a result of the default database transaction being removed from Nautobot core, the `commit` argument has been removed. If a Job author wants to provide users the ability to bypass approval when `approval_required` is set, the Job must implement a `dryrun` variable using the newly-introduced `DryRunVar`. The desired value of the variable will be passed to the `run` method just like any other variable, but the Job author must implement the logic to handle the dry run.

The presence of a `dryrun = DryRunVar()` property on the Job class sets the `supports_dryrun` flag on the Job model, which allows users to bypass approval when `approval_required` is set. To implement a dry run variable without allowing users to bypass approval, the `dryrun` variable should use the `BooleanVar` class instead of `DryRunVar`.

The Job `commit_default` property has been renamed to `dryrun_default` and the default value as well as any existing database values have been flipped.

#### Read-Only Meta Attribute

The `read_only` Job field no longer forces an automatic database rollback at the end of the Job; it is informational only in v2.0.

### Job Registration

All Jobs must be registered in the Celery task registry to be available in Nautobot. This must be accomplished by calling `nautobot.core.celery.register_jobs(*job_classes)` at the top level of a Job module so that it is registered when the module is imported. The `register_jobs` method accepts one or more job classes as arguments.

!!! example
    ```py
    from nautobot.core.celery import register_jobs
    from nautobot.extras.jobs import Job

    class MyJob(Job):
        def run(self):
            pass

    register_jobs(MyJob)
    ```

### Job Logging

All of the custom `log` methods have been removed from the Job class. Instead, use either the Python logger from `nautobot.extras.jobs.get_task_logger` or use `self.logger` in the Job class.

The following table describes the mapping of the old log methods to the new methods:

| Old Method         | New Method             |
| ------------------ | ---------------------- |
| `self.log_debug`   | `self.logger.debug`    |
| `self.log_info`    | `self.logger.info`     |
| `self.log_success` | `self.logger.info`     |
| `self.log_warning` | `self.logger.warning`  |
| `self.log_failure` | `self.logger.error`    |
| `self.log`         | `self.logger.info`     |
| No equivalent      | `self.logger.critical` |

Some logging features from v1.X are accessible when passing a `dict` to the `extra` kwarg in any logger method:

* `logger.debug("message", extra={"skip_db_logging": True})` - Log the message to the console but not to the database
* `logger.debug("message", extra={"object": obj})` - Replaces the `obj` kwarg in Nautobot v1.X Job logging methods
* `logger.debug("message", extra={"grouping": "string"})` - Replaces the `active_test` Job property in Nautobot v1.X

For more detailed documentation on Job logging see the [Job Logging](../index.md#logging) section of the Jobs feature documentation.

### Tracking Job State

`JobResult.status` is now automatically tracked by Celery. Job authors should no longer manually change `self.job_result.status` or `self.job_result.completed` and should instead raise an exception if the Job status should be set to failed (the failed status is now `"FAILURE"`).

The Job's built-in`self.failed` flag, that was used to determine if a Job failed, has been removed. This flag was previously set to `True` automatically when the `log_failure` method was called. Job authors should track their Job's internal state and raise an exception to fail the Job when desired.

### Request Property

The `request` property has been changed to a Celery request instead of a Django request and no longer includes the information from the web request that initiated the Job. The `user` object is now available as `self.user` instead of `self.request.user`.

> *Note:* [Migrating from v1.x to v2.0](../../apps/migration/from-v1.md) provides a general migration guide.
