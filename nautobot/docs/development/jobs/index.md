# Jobs

TODO: Jobs authorship introduction

## Migrating Jobs from v1 to v2

+/- 2.0.0
    See [Migrating Jobs From Nautobot v1](migration/from-v1.md) for more information on how to migrate your existing jobs to Nautobot v2.

## Writing Jobs

Jobs may be installed in one of three ways:

* Manually installed as files in the [`JOBS_ROOT`](../../user-guide/administration/configuration/optional-settings.md#jobs_root) path (which defaults to `$NAUTOBOT_ROOT/jobs/`).
    * The `JOBS_ROOT` directory *must* contain a file named `__init__.py`. Do not delete this file.
    * Each file created within this path is considered a separate module; there is no support for cross-file dependencies (such as a file acting as a common "library" module of functions shared between jobs) for files installed in this way.
* Imported from an external [Git repository](../../user-guide/platform-functionality/gitrepository.md#jobs).
    * The repository's `jobs/` directory *must* contain a file named `__init__.py`.
    * Each Job file in the repository is considered a separate module; there is no support for cross-file dependencies (such as a file acting as a common "library" module of functions shared between jobs) for files installed in this way.
* Packaged as part of a [plugin](../apps/api/platform-features/jobs.md).
    * Jobs installed this way are part of the plugin module and can import code from elsewhere in the plugin or even have dependencies on other packages, if needed, via the standard Python packaging mechanisms.

In any case, each module holds one or more Jobs (Python classes), each of which serves a specific purpose. The logic of each job can be split into a number of distinct methods, each of which performs a discrete portion of the overall job logic.

For example, we can create a module named `devices.py` to hold all of our jobs which pertain to devices in Nautobot. Within that module, we might define several jobs. Each job is defined as a Python class inheriting from `extras.jobs.Job`, which provides the base functionality needed to accept user input and log activity.

+/- 2.0.0
    All job classes must now be registered with `nautobot.core.celery.register_jobs` on module import. For plugins providing jobs, the `register_jobs` method must called from the plugin's `jobs.py` file/submodule at import time. The `register_jobs` method accepts one or more job classes as arguments.

!!! warning
    Make sure you are *not* inheriting `extras.jobs.models.Job` instead, otherwise Django will think you want to define a new database model.

```python
from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job

class CreateDevices(Job):
    ...

class DeviceConnectionsReport(Job):
    ...

class DeviceIPsReport(Job):
    ...

register_jobs(CreateDevices, DeviceConnectionsReport, DeviceIPsReport)
```

Each job class will implement some or all of the following components:

* Module and class attributes, providing for default behavior, documentation and discoverability
* a set of variables for user input via the Nautobot UI (if your job requires any user inputs)
* a `run()` method, which is the only required attribute on a Job class and receives the user input values, if any

It's important to understand that jobs execute on the server asynchronously as background tasks; they log messages and report their status to the database by updating [`JobResult`](../../user-guide/platform-functionality/jobs/models.md#job-results) records and creating [`JobLogEntry`](../../user-guide/platform-functionality/jobs/models.md#job-log-entry) records.

!!! note
    When actively developing a Job utilizing a development environment it's important to understand that the "automatically reload when code changes are detected" debugging functionality provided by `nautobot-server runserver` does **not** automatically restart the Celery `worker` process when code changes are made; therefore, it is required to restart the `worker` after each update to your Job source code or else it will continue to run the version of the Job code that was present when it first started.

    Additionally, as of Nautobot 1.3, the Job database records corresponding to installed Jobs are *not* automatically refreshed when the development server auto-restarts. If you make changes to any of the class and module metadata attributes described in the following sections, the database will be refreshed to reflect these changes only after running `nautobot-server migrate` or `nautobot-server post_upgrade` (recommended) or if you manually edit a Job database record to force it to be refreshed.

### Module Metadata Attributes

#### `name` (Grouping)

You can define a global constant called `name` within a job module (the Python file which contains one or more job classes) to set the default grouping under which jobs in this module will be displayed in the Nautobot UI. If this value is not defined, the module's file name will be used. This "grouping" value may also be defined or overridden when editing Job records in the database.

!!! note
    In some UI elements and API endpoints, the module file name is displayed in addition to or in place of this attribute, so even if defining this attribute, you should still choose an appropriately explanatory file name as well.

### Class Metadata Attributes

Job-specific attributes may be defined under a class named `Meta` within each job class you implement. All of these are optional, but encouraged.

#### `name`

This is the human-friendly name of your job, as will be displayed in the Nautobot UI. If not set, the class name will be used.

!!! note
    In some UI elements and API endpoints, the class name is displayed in addition to or in place of this attribute, so even if defining this attribute, you should still choose an appropriately explanatory class name as well.

#### `description`

An optional human-friendly description of what this job does.
This can accept either plain text or Markdown-formatted text. It can also be multiple lines:

```python
class ExampleJob(Job):
    class Meta:
        description = """
            This job does a number of interesting things.

             1. It hacks the Gibson
             2. It immanentizes the eschaton
             3. It's a floor wax *and* a dessert topping
        """
```

If you code a multi-line description, the first line only will be used in the description column of the jobs list, while the full description will be rendered in the job detail view, submission, approval, and results pages.

#### `approval_required`

Default: `False`

A boolean that will mark this job as requiring approval from another user to be run. For more details on approvals, [please refer to the section on scheduling and approvals](../../user-guide/platform-functionality/jobs/job-scheduling-and-approvals.md).

#### `dryrun_default`

+/- 2.0.0
    The `commit_default` field was renamed to `dryrun_default` and the default value was changed from `True` to `False`. The `commit` functionality that provided an automatic rollback of database changes if the job failed was removed. The `dryrun` functionality was added to provide a way to bypass job approval if a job implements a [`DryRunVar`](#dryrunvar).

Default: `False`

The checkbox to enable dryrun when executing a job is unchecked by default in the Nautobot UI. You can set `dryrun_default` to `True` under the `Meta` class if you want this option to instead be checked by default.

```python
class MyJob(Job):
    class Meta:
        dryrun_default = True
```

#### `field_order`

Default: `[]`

A list of strings (field names) representing the order your job [variables](#variables) should be rendered as form fields in the job submission UI. If not defined, the variables will be listed in order of their definition in the code. If variables are defined on a parent class and no field order is defined, the parent class variables will appear before the subclass variables.

#### `has_sensitive_variables`

+++ 1.3.10

Default: `True`

Unless set to False, it prevents the job's input parameters from being saved to the database. This defaults to True so as to protect against inadvertent database exposure of input parameters that may include sensitive data such as passwords or other user credentials. Review whether each job's inputs contain any such variables before setting this to False; if a job *does* contain sensitive inputs, if possible you should consider whether the job could be re-implemented using Nautobot's [`Secrets`](../../user-guide/platform-functionality/secret.md) feature as a way to ensure that the sensitive data is not directly provided as a job variable at all.

Important notes about jobs with sensitive variables:

* Such jobs cannot be scheduled to run in the future or on a recurring schedule (as scheduled jobs must by necessity store their variables in the database for future reference).
* Jobs with sensitive variables cannot be marked as requiring approval (as jobs pending approval must store their variables in the database until approved).

#### `hidden`

Default: `False`

A Boolean that if set to `True` prevents the job from being displayed by default in the list of Jobs in the Nautobot UI.

Since the jobs execution framework is designed to be generic, there may be several technical jobs defined by users which interact with or are invoked by external systems. In such cases, these jobs are not meant to be executed by a human and likely do not make sense to expose to end users for execution, and thus having them exposed in the UI at all is extraneous.

Important notes about hidden jobs:

* This is merely hiding them by default from the web interface. It is NOT a security feature.
* In the Jobs list view it is possible to filter to "Hidden: (no selection)" or even "Hidden: Yes" to list the hidden jobs.
* All Job UI and REST API endpoints still exist for hidden jobs and can be accessed by any user who is aware of their existence.
* Hidden jobs can still be executed through the UI or the REST API given the appropriate URL.
* Results for hidden jobs will still appear in the Job Results list after they are run.

#### `read_only`

+++ 1.1.0

+/- 2.0.0
    The `read_only` flag no longer changes the behavior of Nautobot core and is up to the job author to decide whether their job should be considered read only.

Default: `False`

A boolean that can be set by the job author to indicate that the job does not make any changes to the environment. What behavior makes each job "read only" is up to the individual job author to decide. Note that user input may still be optionally collected with read-only jobs via job variables, as described below.

#### `soft_time_limit`

+++ 1.3.0

An int or float value, in seconds, which can be used to override the default [soft time limit](../../user-guide/administration/configuration/optional-settings.md#celery_task_soft_time_limit) for a job task to complete.

The `celery.exceptions.SoftTimeLimitExceeded` exception will be raised when this soft time limit is exceeded. The job task can catch this to clean up before the [hard time limit](../../user-guide/administration/configuration/optional-settings.md#celery_task_time_limit) (10 minutes by default) is reached:

```python
from celery.exceptions import SoftTimeLimitExceeded
from nautobot.extras.jobs import Job

class ExampleJobWithSoftTimeLimit(Job):
    class Meta:
        name = "Soft Time Limit"
        description = "Set a soft time limit of 10 seconds`"
        soft_time_limit = 10

    def run(self):
        try:
            # code which might take longer than 10 seconds to run
            job_code()
        except SoftTimeLimitExceeded:
            # any clean up code
            cleanup_in_a_hurry()
```

#### `task_queues`

+++ 1.5.0

Default: `[]`

A list of task queue names that the job can be routed to. An empty list will default to only allowing the user to select the [default queue](../../user-guide/administration/configuration/optional-settings.md#celery_task_default_queue) (`default` unless changed by an administrator). The first queue in the list will be used if a queue is not specified in a job run API call.

!!! note
    A worker must be listening on the requested queue or the job will not run. See the documentation on [task queues](../../user-guide/administration/guides/celery-queues.md) for more information.

#### `template_name`

+++ 1.4.0

A path relative to the job source code containing a Django template which provides additional code to customize the Job's submission form. This template should extend the existing job template, `extras/job.html`, otherwise the base form and functionality may not be available.

A template can provide additional JavaScript, CSS, or even display HTML. A good starting template would be:

```html
{% extends 'extras/job.html' %}

{% block extra_styles %}
    {{ block.super }}
    <!-- Add additional CSS here. -->
{% endblock %}
{% block content %}
    {{ block.super }}
    <!-- Add additional HTML here. -->
{% endblock content %}
{% block javascript %}
    {{ block.super }}
    <!-- Add additional JavaScript here. -->
{% endblock javascript %}
```

For another example checkout [the template used in example plugin](https://github.com/nautobot/nautobot/blob/next/examples/example_plugin/example_plugin/templates/example_plugin/example_with_custom_template.html) in the GitHub repo.

#### `time_limit`

+++ 1.3.0

An int or float value, in seconds, which can be used to override the
default [hard time limit](../../user-guide/administration/configuration/optional-settings.md#celery_task_time_limit) (10 minutes by default) for a job task to complete.

Unlike the `soft_time_limit` above, no exceptions are raised when a `time_limit` is exceeded. The task will just terminate silently:

```python
from nautobot.extras.jobs import Job

class ExampleJobWithHardTimeLimit(Job):
    class Meta:
        name = "Hard Time Limit"
        description = "Set a hard time limit of 10 seconds`"
        time_limit = 10

    def run(self):
        # code which might take longer than 10 seconds to run
        # this code will fail silently if the time_limit is exceeded
        job_code()
```

!!! note
    If the `time_limit` is set to a value less than or equal to the `soft_time_limit`, a warning log is generated to inform the user that this job will fail silently after the `time_limit` as the `soft_time_limit` will never be reached.

### Variables

Variables allow your job to accept user input via the Nautobot UI, but they are optional; if your job does not require any user input, there is no need to define any variables. Conversely, if you are making use of user input in your job, you *must* also implement the `run()` method, as it is the only entry point to your job that has visibility into the variable values provided by the user.

```python
from nautobot.extras.jobs import Job, StringVar, IntegerVar, ObjectVar

class CreateDevices(Job):
    var1 = StringVar(...)
    var2 = IntegerVar(...)
    var3 = ObjectVar(...)

    def run(self, var1, var2, var3):
        ...
```

The remainder of this section documents the various supported variable types and how to make use of them.

#### Default Variable Options

All job variables support the following default options:

* `default` - The field's default value
* `description` - A brief user-friendly description of the field
* `label` - The field name to be displayed in the rendered form
* `required` - Indicates whether the field is mandatory (all fields are required by default)
* `widget` - The class of form widget to use (see the [Django documentation](https://docs.djangoproject.com/en/stable/ref/forms/widgets/))

#### `StringVar`

Stores a string of characters (i.e. text). Options include:

* `min_length` - Minimum number of characters
* `max_length` - Maximum number of characters
* `regex` - A regular expression against which the provided value must match

Note that `min_length` and `max_length` can be set to the same number to effect a fixed-length field.

#### `TextVar`

Arbitrary text of any length. Renders as a multi-line text input field.

#### `IntegerVar`

Stores a numeric integer. Options include:

* `min_value` - Minimum value
* `max_value` - Maximum value

#### `BooleanVar`

A true/false flag. This field has no options beyond the defaults listed above.

#### `DryRunVar`

A true/false flag with special handling for jobs that require approval. If `dryrun = DryRunVar()` is declared on a job class, approval may be bypassed if `dryrun` is set to `True` on job execution.

#### `ChoiceVar`

A set of choices from which the user can select one.

* `choices` - A list of `(value, label)` tuples representing the available choices. For example:

```python
CHOICES = (
    ('n', 'North'),
    ('s', 'South'),
    ('e', 'East'),
    ('w', 'West')
)

direction = ChoiceVar(choices=CHOICES)
```

In the example above, selecting the choice labeled "North" will submit the value `n`.

#### `MultiChoiceVar`

Similar to `ChoiceVar`, but allows for the selection of multiple choices.

#### `ObjectVar`

A particular object within Nautobot. Each ObjectVar must specify a particular model, and allows the user to select one of the available instances. ObjectVar accepts several arguments, listed below.

* `model` - The model class
* `display_field` - The name of the REST API object field to display in the selection list (default: `'display'`)
* `query_params` - A dictionary of REST API query parameters to use when retrieving available options (optional)
* `null_option` - A label representing a "null" or empty choice (optional)

The `display_field` argument is useful in cases where using the `display` API field is not desired for referencing the object. For example, when displaying a list of IP Addresses, you might want to use the `dns_name` field:

```python
device_type = ObjectVar(
    model=IPAddress,
    display_field="dns_name",
)
```

To limit the selections available within the list, additional query parameters can be passed as the `query_params` dictionary. For example, to show only devices with an "active" status:

```python
device = ObjectVar(
    model=Device,
    query_params={
        'status': 'active'
    }
)
```

Multiple values can be specified by assigning a list to the dictionary key. It is also possible to reference the value of other fields in the form by prepending a dollar sign (`$`) to the variable's name. The keys you can use in this dictionary are the same ones that are available in the REST API - as an example it is also possible to filter the `Location` `ObjectVar` for its `location_type` and `tenant_group`.

```python
location_type = ObjectVar(
    model=LocationType
)
tenant_group = ObjectVar(
    model=TenantGroup
)
location = ObjectVar(
    model=Location,
    query_params={
        "location_type": "$location_type",
        "tenant_group": "$tenant_group"
    }
)
```

#### `MultiObjectVar`

Similar to `ObjectVar`, but allows for the selection of multiple objects.

#### `FileVar`

An uploaded file. Note that uploaded files are present in memory only for the duration of the job's execution: They will not be automatically saved for future use. The job is responsible for writing file contents to disk where necessary.

#### `IPAddressVar`

An IPv4 or IPv6 address, without a mask. Returns a `netaddr.IPAddress` object.

#### `IPAddressWithMaskVar`

An IPv4 or IPv6 address with a mask. Returns a `netaddr.IPNetwork` object which includes the mask.

#### `IPNetworkVar`

An IPv4 or IPv6 network with a mask. Returns a `netaddr.IPNetwork` object. Two attributes are available to validate the provided mask:

* `min_prefix_length` - Minimum length of the mask
* `max_prefix_length` - Maximum length of the mask

### The `run()` Method

The `run()` method must be implemented. After the `self` argument, it should accept keyword arguments for any variables defined on the job:

```python
from nautobot.extras.jobs import Job, StringVar, IntegerVar, ObjectVar

class CreateDevices(Job):
    var1 = StringVar(...)
    var2 = IntegerVar(...)
    var3 = ObjectVar(...)

    def run(self, var1, var2, var3):
        ...
```

Again, defining user variables is totally optional; you may create a job with a `run()` method with only the `self` argument if no user input is needed.

!!! warning
    When writing Jobs that create and manipulate data it is recommended to make use of the `validated_save()` convenience method which exists on all core models. This method saves the instance data but first enforces model validation logic. Simply calling `save()` on the model instance **does not** enforce validation automatically and may lead to bad data. See the development [best practices](../core/best-practices.md).

!!! warning
    The Django ORM provides methods to create/edit many objects at once, namely `bulk_create()` and `update()`. These are best avoided in most cases as they bypass a model's built-in validation and can easily lead to database corruption if not used carefully.

--- 2.0.0
    The NetBox backwards compatible `test_*()` and `post_run()` methods have been removed.

### Logging

+/- 2.0.0

Messages logged from a job's logger will be stored in [`JobLogEntry`](../../user-guide/platform-functionality/jobs/models.md#job-log-entry) records associated with the current [`JobResult`](../../user-guide/platform-functionality/jobs/models.md#job-results).

The logger can be accessed either by using the `logger` property on the job class or `nautobot.extras.jobs.get_task_logger(__name__)`. Both will return the same logger instance. For more information on the standard Python logging module, see the [Python documentation](https://docs.python.org/3/library/logging.html).

An optional `grouping` and/or `object` may be provided in log messages by passing them in the log function call's `extra` kwarg. If a `grouping` is not provided it will default to the function name that logged the message. The `object` will default to `None`.

!!! example
    ```py
    from nautobot.extras.jobs import BaseJob

    class MyJob(BaseJob):
        def run(self):
            logger.info("This job is running!", extra={"grouping": "myjobisrunning", "object": self.job_result})
    ```

To skip writing a log entry to the database, set the `skip_db_logging` key in the "extra" kwarg to `True` when calling the log function. The output will still be written to the console.

!!! example
    ```py
    from nautobot.extras.jobs import BaseJob

    class MyJob(BaseJob):
        def run(self):
            logger.info("This job is running!", extra={"skip_db_logging": True})
    ```

Markdown rendering is supported for log messages.

+/- 1.3.4
    As a security measure, the `message` passed to any of these methods will be passed through the `nautobot.core.utils.logging.sanitize()` function in an attempt to strip out information such as usernames/passwords that should not be saved to the logs. This is of course best-effort only, and Job authors should take pains to ensure that such information is not passed to the logging APIs in the first place. The set of redaction rules used by the `sanitize()` function can be configured as [settings.SANITIZER_PATTERNS](../../user-guide/administration/configuration/optional-settings.md#sanitizer_patterns).

+/- 2.0.0
    The Job class logging functions (example: `self.log(message)`, `self.log_success(obj=None, message=message)`, etc) have been removed. Also, the convenience method to mark a job as failed, `log_failure()`, has been removed. To replace the functionality of this method, you can log an error message with `self.logger.error()` and then raise an exception to fail the job. Note that it is no longer possible to manually set the job result status as failed without raising an exception in the job.

+/- 2.0.0
    The `AbortTransaction` class was moved from the `nautobot.utilities.exceptions` module to `nautobot.core.exceptions`.

### Marking a Job as Failed

To mark a job as failed, raise an exception from within the `run()` method. The exception message will be logged to the traceback of the job result. The job result status will be set to `failed`. To output a job log message you can use the `self.logger.error()` method.

```python

As an example, the following job will fail if the user does not put the word "Taco" in `var1`:

```python
from nautobot.extras.jobs import Job, StringVar

class MyJob(Job):
    var1 = StringVar(...)

    def run(self, var1):
        if var1 != "Taco":
            self.logger.error("var1 must be 'Taco'")
            raise Exception("Argument input validation failed.")
```

### Accessing User and Job Result

+/- 2.0.0
    The `request` property has been changed to a Celery request instead of a Django web request and no longer includes the information from the web request that initiated the Job. The `user` object is now available as `self.user` instead of `self.request.user`.

The user that initiated the job and the job result associated to the job can be accessed through properties on the job class:

```py
username = self.user.username
job_result_id = self.job_result.id
self.logger.info("Job %s initiated by user %s is running.", job_result_id, username)
```

### Reading Data from Files

The `Job` class provides two convenience methods for reading data from files:

* `load_yaml`
* `load_json`

These two methods will load data in YAML or JSON format, respectively, from files within the local path (i.e. `JOBS_ROOT/`).

## Testing Jobs

Jobs are Python code and can be tested as such, usually via [Django unit-test features](https://docs.djangoproject.com/en/stable/topics/testing/). That said, there are a few useful tricks specific to testing Jobs.

While individual methods within your Job can and should be tested in isolation, you'll likely also want to test the entire execution of the Job. Nautobot 1.3.3 introduced a few enhancements to make this simpler to do, but it's also quite possible to test in earlier releases with a bit more effort.

### Nautobot 1.3.3 and later

The simplest way to test the entire execution of Jobs from 1.3.3 on is via calling the `nautobot.core.testing.run_job_for_testing()` method, which is a helper wrapper around the `JobResult.enqueue_job` function used to execute a Job via Nautobot's Celery worker process.

+/- 2.0.0
    `run_job_for_testing` was moved from the `nautobot.utilities.testing` module to `nautobot.core.testing`.

Because of the way `run_job_for_testing` and more specifically Celery tasks work, which is somewhat complex behind the scenes, you need to inherit from `nautobot.core.testing.TransactionTestCase` instead of `django.test.TestCase` (Refer to the [Django documentation](https://docs.djangoproject.com/en/stable/topics/testing/tools/#provided-test-case-classes) if you're interested in the differences between these classes - `TransactionTestCase` from Nautobot is a small wrapper around Django's `TransactionTestCase`).

When using `TransactionTestCase` (whether from Django or from Nautobot) each tests runs on a completely empty database. Furthermore, Nautobot requires new jobs to be enabled before they can run. Therefore, we need to make sure the job is enabled before each run which `run_job_for_testing` handles for us.

A simple example of a Job test case for 1.3.3 and forward might look like the following:

```python
from nautobot.core.testing import run_job_for_testing, TransactionTestCase
from nautobot.extras.models import Job, JobLogEntry


class MyJobTestCase(TransactionTestCase):
    def test_my_job(self):
        # Testing of Job "MyJob" in file "my_job_file.py" in $JOBS_ROOT
        job = Job.objects.get(job_class_name="MyJob", module_name="my_job_file", source="local")
        # or, job = Job.objects.get_for_class_path("local/my_job_file/MyJob")
        job_result = run_job_for_testing(job, var1="abc", var2=123)

        # Inspect the logs created by running the job
        log_entries = JobLogEntry.objects.filter(job_result=job_result)
        for log_entry in log_entries:
            self.assertEqual(log_entry.message, "...")
```

!!! tip
    For more advanced examples refer to the Nautobot source code, specifically `nautobot/extras/tests/test_jobs.py`.

## Debugging job performance

+++ 1.5.17

Debugging the performance of Nautobot jobs can be tricky, because they are executed in the worker context. In order to gain extra visibility, [cProfile](https://docs.python.org/3/library/profile.html) can be used to profile the job execution.

The 'profile' form field on jobs is automatically available when the `DEBUG` settings is `True`. When you select that checkbox, a profiling report in the pstats format will be written to the file system of the environment where the job runs. Normally, this is on the file system of the worker process, but if you are using the `nautobot-server runjob` command with `--local`, it will end up in the file system of the web application itself. The path of the written file will be logged in the job.

!!! note
    If you need to run this in an environment where `DEBUG` is `False`, you have the option of using `nautobot-server runjob` with the `--profile` flag. According to the docs, `cProfile` should have minimal impact on the performance of the job; still, proceed with caution when using this in a production environment.

### Reading profiling reports

A full description on how to deal with the output of `cProfile` can be found in the [Instant User's Manual](https://docs.python.org/3/library/profile.html#instant-user-s-manual), but here is something to get you started:

```python
import pstats
job_result_uuid = "66b70231-002f-412b-8cc4-1cc9609c2c9b"
stats = pstats.Stats(f"/tmp/job-result-{job_result_uuid}.pstats")
stats.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(10)
```

This will print the 10 functions that the job execution spent the most time in - adapt this to your needs!

## Example Jobs

### Creating objects for a planned location

This job prompts the user for three variables:

* The name of the new location
* The device model (a filtered list of defined device types)
* The number of access switches to create

These variables are presented as a web form to be completed by the user. Once submitted, the job's `run()` method is called to create the appropriate objects, and it returns simple CSV output to the user summarizing the created objects.

```python
from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Location, LocationType, Device, Manufacturer, DeviceType
from nautobot.extras.models import Status, Role
from nautobot.extras.jobs import Job, StringVar, IntegerVar, ObjectVar


class NewBranch(Job):
    class Meta:
        name = "New Branch"
        description = "Provision a new branch location"
        field_order = ["location_name", "switch_count", "switch_model"]

    location_name = StringVar(description="Name of the new location")
    switch_count = IntegerVar(description="Number of access switches to create")
    manufacturer = ObjectVar(model=Manufacturer, required=False)
    switch_model = ObjectVar(
        description="Access switch model", model=DeviceType, query_params={"manufacturer_id": "$manufacturer"}
    )

    def run(self, location_name, switch_count, switch_model):
        STATUS_PLANNED = Status.objects.get(name="Planned")

        # Create the new location
        root_type = LocationType.objects.get_or_create(name="Campus")
        location = Location(
            name=location_name,
            location_type=root_type,
            status=STATUS_PLANNED,
        )
        location.validated_save()
        self.logger.info("Created new location", extra={"object": location})

        # Create access switches
        device_ct = ContentType.objects.get_for_model(Device)
        switch_role = Role.objects.get(name="Access Switch")
        switch_role.content_types.add(device_ct)
        for i in range(1, switch_count + 1):
            switch = Device(
                device_type=switch_model,
                name=f"{location.name}-switch{i}",
                location=location,
                status=STATUS_PLANNED,
                role=switch_role,
            )
            switch.validated_save()
            self.logger.info("Created new switch", extra={"object": switch})

        # Generate a CSV table of new devices
        output = ["name,make,model"]
        for switch in Device.objects.filter(location=location):
            attrs = [switch.name, switch.device_type.manufacturer.name, switch.device_type.model]
            output.append(",".join(attrs))

        return "\n".join(output)
```

### Device validation

A job to perform various validation of Device data in Nautobot. As this job does not require any user input, it does not define any variables, nor does it implement a `run()` method.

```python
from nautobot.dcim.models import ConsolePort, Device, PowerPort
from nautobot.extras.models import Status
from nautobot.extras.jobs import Job


class DeviceConnectionsReport(Job):
    description = "Validate the minimum physical connections for each device"

    def test_console_connection(self):
        STATUS_ACTIVE = Status.objects.get(name='Active')

        # Check that every console port for every active device has a connection defined.
        for console_port in ConsolePort.objects.select_related('device').filter(device__status=STATUS_ACTIVE):
            if console_port.connected_endpoint is None:
                self.logger.error(
                    "No console connection defined for %s",
                    console_port.name,
                    extra={"object": console_port.device},
                )
            elif not console_port.connection_status:
                self.logger.warning(
                    "Console connection for %s marked as planned",
                    console_port.name,
                    extra={"object": console_port.device},
                )
            else:
                self.logger.info(
                    "Console port %s has a connection defined",
                    console_port.name,
                    extra={"object": console_port.device},
                )

    def test_power_connections(self):
        STATUS_ACTIVE = Status.objects.get(name='Active')

        # Check that every active device has at least two connected power supplies.
        for device in Device.objects.filter(status=STATUS_ACTIVE):
            connected_ports = 0
            for power_port in PowerPort.objects.filter(device=device):
                if power_port.connected_endpoint is not None:
                    connected_ports += 1
                    if not power_port.connection_status:
                        self.logger.warning(
                            "Power connection for %s marked as planned",
                            power_port.name,
                            extra={"object": device},
                        )
            if connected_ports < 2:
                self.logger.error(
                    "%s connected power supplies found (2 needed)",
                    connected_ports,
                    extra={"object": device},
                )
            else:
                self.logger.info("At least two connected power supplies found", extra={"object": device})
```

## Job Button Receivers

Job Buttons are only able to initiate a specific type of job called a **Job Button Receiver**. These are jobs that subclass the `nautobot.extras.jobs.JobButtonReceiver` class. Job Button Receivers are similar to normal jobs except they are hard coded to accept only `object_pk` and `object_model_name` [variables](#variables). Job Button Receivers are hidden from the jobs listing UI by default but otherwise function similarly to other jobs. The `JobButtonReceiver` class only implements one method called `receive_job_button`.

!!! note
    Job Button Receivers still need to be [enabled through the web UI](../../user-guide/platform-functionality/jobs/index.md#enabling-jobs-for-running) before they can be used just like other Jobs.

### The `receive_job_button()` Method

All `JobButtonReceiver` subclasses must implement a `receive_job_button()` method. This method accepts only one argument:

1. `obj` - An instance of the object where the button was pressed

### Example Job Button Receiver

```py
from nautobot.extras.jobs import JobButtonReceiver


class ExampleSimpleJobButtonReceiver(JobButtonReceiver):
    class Meta:
        name = "Example Simple Job Button Receiver"

    def receive_job_button(self, obj):
        self.logger.info("Running Job Button Receiver.", extra={"object": obj})
        # Add job logic here
```

### Job Buttons for Multiple Types

Since Job Buttons can be associated to multiple object types, it would be trivial to create a Job that can change what it runs based on the object type.

```py
from nautobot.dcim.models import Device, Location
from nautobot.extras.jobs import JobButtonReceiver


class ExampleComplexJobButtonReceiver(JobButtonReceiver):
    class Meta:
        name = "Example Complex Job Button Receiver"

    def _run_location_job(self, obj):
        self.logger.info("Running Location Job Button Receiver.", extra={"object": obj})
        # Run Location Job function

    def _run_device_job(self, obj):
        self.logger.info("Running Device Job Button Receiver.", extra={"object": obj})
        # Run Device Job function

    def receive_job_button(self, obj):
        user = self.user
        if isinstance(obj, Location):
            if not user.has_perm("dcim.add_location"):
                self.logger.error("User '%s' does not have permission to add a Location.", user, extra={"object": obj})
                raise Exception("User does not have permission to add a Location.")
            else:
                self._run_location_job(obj)
        elif isinstance(obj, Device):
            if not user.has_perm("dcim.add_device"):
                self.logger.error("User '%s' does not have permission to add a Device.", user, extra={"object": obj})
                raise Exception("User does not have permission to add a Device.")
            else:
                self._run_device_job(obj)
        else:
            self.logger.error("Unable to run Job Button for type %s.", type(obj).__name__, extra={"object": obj})
            raise Exception("Job button called on unsupported object type.")

```

## Job Hook Receivers

Job Hooks are only able to initiate a specific type of job called a **Job Hook Receiver**. These are jobs that subclass the `nautobot.extras.jobs.JobHookReceiver` class. Job hook receivers are similar to normal jobs except they are hard coded to accept only an `object_change` [variable](#variables). Job Hook Receivers are hidden from the jobs listing UI by default but otherwise function similarly to other jobs. The `JobHookReceiver` class only implements one method called `receive_job_hook`.

!!! warning
    Requiring approval for execution of Job Hooks by setting the `Meta.approval_required` attribute to `True` on your `JobHookReceiver` subclass is not supported. The value of this attribute will be ignored. Support for requiring approval of Job Hooks will be added in a future release.

!!! important
    To prevent negatively impacting system performance through an infinite loop, a change that was made by a `JobHookReceiver` job will not trigger another `JobHookReceiver` job to run.

### Example Job Hook Receiver

```py
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.jobs import JobHookReceiver


class ExampleJobHookReceiver(JobHookReceiver):
    def receive_job_hook(self, change, action, changed_object):
        # return on delete action
        if action == ObjectChangeActionChoices.ACTION_DELETE:
            return

        # log diff output
        snapshots = change.get_snapshots()
        self.logger.info("DIFF: %s", snapshots['differences'])

        # validate changes to serial field
        if "serial" in snapshots["differences"]["added"]:
            old_serial = snapshots["differences"]["removed"]["serial"]
            new_serial = snapshots["differences"]["added"]["serial"]
            self.logger.info("%s serial has been changed from %s to %s", changed_object, old_serial, new_serial)

            # Check the new serial is valid and revert if necessary
            if not self.validate_serial(new_serial):
                changed_object.serial = old_serial
                changed_object.save()
                self.logger.info("%s serial %s was not valid. Reverted to %s", changed_object, new_serial, old_serial)

            self.logger.info("Serial validation completed for %s", changed_object)

    def validate_serial(self, serial):
        # add business logic to validate serial
        return False
```

### The `receive_job_hook()` Method

All `JobHookReceiver` subclasses must implement a `receive_job_hook()` method. This method accepts three arguments:

1. `change` - An instance of `nautobot.extras.models.ObjectChange`
2. `action` - A string with the action performed on the changed object ("create", "update" or "delete")
3. `changed_object` - An instance of the object that was changed, or `None` if the object has been deleted
