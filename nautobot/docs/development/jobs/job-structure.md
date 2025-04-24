# Job Structure

## Introduction

Jobs in Nautobot are Python classes designed to perform automated tasks within the Nautobot environment. Each Job can consist of:

- **Metadata attributes** — control how the Job appears and behaves in the UI (e.g. name, permissions, scheduling rules)
- **Input variables** — define the user-supplied inputs for the Job
- **Special methods** — control the execution flow (`run()`, `on_success()`, etc.)
- **Registration logic** — every Job must be explicitly registered with `register_jobs()` to be discoverable

It’s essential to distinguish between metadata attributes and input variables clearly:

- **Metadata Attributes** define how the Job itself behaves within the Nautobot platform (such as display name, permissions, execution constraints).
- **Input Variables** define user-supplied inputs that can influence the Job’s execution logic.

Below, each section details how to implement these components in your Jobs effectively.

## Job Class vs. Job Record

Nautobot separates the **Job class** (your Python code) from the **Job record** (a database entry that stores metadata).

| Job Class                     | Job Record                    |
|------------------------------|-------------------------------|
| Python code in a module      | Created automatically by Nautobot |
| Inherits from `Job`          | Stored in the database        |
| Defines metadata, variables, logic | Stores enabled state, name override, queue config |
| Discovered on startup        | Updated by `post_upgrade` or Git resync |

The Job record must exist for the Job to run — but Nautobot always executes the logic from your source code. This separation allows changes to the Job source without modifying the database.

## Job Registration

All Job classes must be registered with Nautobot at import time to be discoverable and runnable.

This is done using the `register_jobs()` helper:

```python
from nautobot.apps.jobs import Job, register_jobs

class HelloWorldJob(Job):
    ...

register_jobs(HelloWorldJob)
```

You can register multiple jobs at once:

```python
register_jobs(CleanupDevices, SyncInventory)
```

### Where to Register

- For files in `JOBS_ROOT`, register Jobs directly in the file or from a top-level `__init__.py` that imports submodules.
- For Git-based Jobs, use the `jobs/__init__.py` file in the repo to register all your Job classes.
- For App-based Jobs, register them in the module defined by your App’s `NautobotAppConfig.jobs` property (default: `jobs`).

If you don’t call `register_jobs()`, Nautobot will skip your class during startup, even if it's defined correctly.

!!! warning "Unregistered Jobs are invisible"
    If you forget to call `register_jobs()`, Nautobot won't discover your Job — it won't appear in the UI, API, or be runnable at all.

## Module Metadata Attributes

### `name` (Grouping)

You can define a global constant called `name` within a job module (the Python file which contains one or more Job classes) to set the default grouping under which the Jobs in this module will be displayed in the Nautobot UI. If this value is not defined, the module's file name will be used. This "grouping" value may also be defined or overridden when editing Job records in the database.

!!! note
    In some UI elements and API endpoints, the module file name is displayed in addition to or in place of this attribute, so even if defining this attribute, you should still choose an appropriately explanatory file name as well.

## Class Metadata Attributes

Job-specific attributes may be defined under a class named `Meta` within each Job class you implement. All of these are optional but encouraged for clearer user experience and administration.

### `name`

This is the human-friendly name of your Job, as displayed in the Nautobot UI. If not set, the class name will be used.

!!! note
    In some UI elements and API endpoints, the class name is displayed in addition to or in place of this attribute, so even if defining this attribute, you should still choose an appropriately explanatory class name as well.

### `description`

An optional human-friendly description of what this Job does. This can accept either plain text, Markdown-formatted text, or [a limited subset of HTML](../../user-guide/platform-functionality/template-filters.md#render_markdown). It can also be multiple lines:

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

If you code a multi-line description, the first line only will be used in the description column of the Jobs list, while the full description will be rendered in the Job detail view, submission, approval, and results pages.


### `approval_required`

Default: `False`

A boolean that will mark this Job as requiring approval from another user to be run. For more details on approvals, [please refer to the section on scheduling and approvals](../../user-guide/platform-functionality/jobs/job-scheduling-and-approvals.md).

### `dryrun_default`

+/- 2.0.0 "Replacement for `commit_default`"
    The `commit_default` field was renamed to `dryrun_default` and the default value was changed from `True` to `False`. The `commit` functionality that provided an automatic rollback of database changes if the Job failed was removed.

Default: `False`

If the Job implements a [`DryRunVar`](#dryrunvar), what its default value should be.
The checkbox to enable dryrun when executing a Job is unchecked by default in the Nautobot UI. You can set `dryrun_default` to `True` under the `Meta` class if you want this option to instead be checked by default.

```python
class MyJob(Job):
    class Meta:
        dryrun_default = True
```

### `field_order`

Default: `[]`

A list of strings (field names) representing the order your Job [variables](#variables) should be rendered as form fields in the Job submission UI. If not defined, the variables will be listed in order of their definition in the code. If variables are defined on a parent class and no field order is defined, the parent class variables will appear before the subclass variables.

### `has_sensitive_variables`

Default: `True`

Unless set to False, it prevents the Job's input parameters from being saved to the database. This defaults to True so as to protect against inadvertent database exposure of input parameters that may include sensitive data such as passwords or other user credentials. Review whether each Job's inputs contain any such variables before setting this to False; if a Job *does* contain sensitive inputs, if possible you should consider whether the Job could be re-implemented using Nautobot's [Secrets](../../user-guide/platform-functionality/secret.md) feature as a way to ensure that the sensitive data is not directly provided as a Job variable at all.

Important notes about Jobs with sensitive variables:

* Such Jobs cannot be scheduled to run in the future or on a recurring schedule (as Scheduled Jobs must by necessity store their variables in the database for future reference).
* Jobs with sensitive variables cannot be marked as requiring approval (as Jobs pending approval must store their variables in the database until approved).

### `hidden`

Default: `False`

A Boolean that if set to `True` prevents the Job from being displayed by default in the list of Jobs in the Nautobot UI.

Since the Job execution framework is designed to be generic, there may be several technical Jobs defined by users which interact with or are invoked by external systems. In such cases, these Jobs are not meant to be executed by a human and likely do not make sense to expose to end users for execution, and thus having them exposed in the UI at all is extraneous.

Important notes about hidden Jobs:

* This is merely hiding them by default from the web interface. It is NOT a security feature.
* In the Jobs list view it is possible to filter to "Hidden: (no selection)" or even "Hidden: Yes" to list the hidden Jobs.
* All Job UI and REST API endpoints still exist for hidden Jobs and can be accessed by any user who is aware of their existence.
* Hidden Jobs can still be executed through the UI or the REST API given the appropriate URL.
* Results for hidden Jobs will still appear in the Job Results list after they are run.

### `is_singleton`

+++ 2.4.0

Default: `False`
A Boolean that if set to `True` prevents the job from running twice simultaneously.

Any duplicate job instances will error out with a singleton-specific error message.

Important notes about singleton jobs:

* The singleton functionality is implemented with a Redis key set to timeout either on the hard time out of the job or whenever the job terminates.
    * Therefore, a restart of Redis will wipe the singleton locks
* A checkbox on the job run form makes it possible to force the singleton lock to be overridden. This makes it possible to recover from failure scenarios such as the original singleton job being stopped before it can unset the lock.

### `read_only`

+/- 2.0.0 "No automatic functionality"
    The `read_only` flag no longer changes the behavior of Nautobot core and is up to the Job author to decide whether their Job should be considered read only.

Default: `False`

A boolean that can be set by the Job author to indicate that the Job does not make any changes to the environment. What behavior makes each Job "read only" is up to the individual Job author to decide. Note that user input may still be optionally collected with read-only Jobs via Job variables, as described below.

### `soft_time_limit`

An int or float value, in seconds, which can be used to override the default [soft time limit](../../user-guide/administration/configuration/settings.md#celery_task_soft_time_limit) for a Job task to complete.

The `celery.exceptions.SoftTimeLimitExceeded` exception will be raised when this soft time limit is exceeded. The Job task can catch this to clean up before the [hard time limit](../../user-guide/administration/configuration/settings.md#celery_task_time_limit) (10 minutes by default) is reached:

```python
from celery.exceptions import SoftTimeLimitExceeded
from nautobot.apps.jobs import Job

class ExampleJobWithSoftTimeLimit(Job):
    class Meta:
        name = "Soft Time Limit"
        description = "Set a soft time limit of 10 seconds"
        soft_time_limit = 10

    def run(self):
        try:
            # code which might take longer than 10 seconds to run
            job_code()
        except SoftTimeLimitExceeded:
            # any clean up code
            cleanup_in_a_hurry()
```

### `task_queues`

Default: `[]`

A list of Job Queue names that the Job can be routed to. An empty list will default to only allowing the user to select the [default Celery queue](../../user-guide/administration/configuration/settings.md#celery_task_default_queue) (`default` unless changed by an administrator). The queue specified in the Job's `default_job_queue` will be used if a queue is not specified in a Job run API call.

+/- 2.4.0 "Changed default queue selection"
    As a result of the addition of Job Queues, the default queue when running a Job without explicitly selecting a queue is now the job queue specified in the `default_job_queue` field on the Job model. `default_job_queue` fields for any existing Job instances are automatically populated with the name of the first entry in `task_queues` list of the Job class. When `task_queues` list on the Job class is empty, the corresponding Job instance's `default_job_queue` will be the job queue with the name provided by `settings.CELERY_TASK_DEFAULT_QUEUE`. You can also override the initial `default_job_queue` by setting `default_job_queue_override` to True and assign the field with a different Job Queue instance.

!!! note
    A worker must be listening on the requested queue or the Job will not run. See the documentation on [task queues](../../user-guide/administration/guides/celery-queues.md) for more information.

### `template_name`

A path relative to the Job source code containing a Django template which provides additional code to customize the Job's submission form. This template should extend the existing Job template, `extras/job.html`, otherwise the base form and functionality may not be available.

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

+++ 2.2.0 "Additional blocks"
    Added the `job_form` and `schedule_form` sub-blocks to `extras/job.html`, for use by Jobs that just want to override the rendered forms without replacing all of `{% block content %}`.

For another example checkout [the template used in the Example App](https://github.com/nautobot/nautobot/blob/main/examples/example_app/example_app/templates/example_app/example_with_custom_template.html) in the GitHub repo.

### `time_limit`

An int or float value, in seconds, which can be used to override the
default [hard time limit](../../user-guide/administration/configuration/settings.md#celery_task_time_limit) (10 minutes by default) for a Job task to complete.

Unlike the `soft_time_limit` above, no exceptions are raised when a `time_limit` is exceeded. The task will just terminate silently:

```python
from nautobot.apps.jobs import Job

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

!!! note "`time_limit` versus `soft_time_limit`"
    If the `time_limit` is set to a value less than or equal to the `soft_time_limit`, a warning log is generated to inform the user that this Job will fail silently after the `time_limit` as the `soft_time_limit` will never be reached.

## Variables

Variables allow your Job to accept user input via the Nautobot UI, but they are optional; if your Job does not require any user input, there is no need to define any variables. Conversely, if you are making use of user input in your Job, you *must* also implement the `run()` method, as it is the only entry point to your Job that has visibility into the variable values provided by the user.

This example defines two input variables using `StringVar` and `IntegerVar`, which are passed as keyword arguments into the `run()` method. The values provided by the user at runtime are then used inside a loop to print a customized greeting message using `self.logger.info()`. By logging each message, the Job provides immediate feedback in the JobResult view. Finally, the class is registered using `register_jobs()` to ensure it can be discovered and run within Nautobot.

```python
from nautobot.apps import jobs

name = "Hello Jobs"

class HelloJobs(jobs.Job):
    class Meta:
        name = "Say Hello"

    person_name = jobs.StringVar(
        description="Name of the person to greet",
        default="world"
    )

    greeting_count = jobs.IntegerVar(
        description="How many times to greet",
        default=1,
        min_value=1
    )

    def run(self, *, person_name, greeting_count):
        for i in range(greeting_count):
            self.logger.info("Hello, %s! (%d)", person_name, i + 1)

jobs.register_jobs(HelloJobs)
```

The remainder of this section documents the various supported variable types and how to make use of them.

### Default Variable Options

All Job variables support the following default options:

* `default` - The field's default value
* `description` - A brief user-friendly description of the field
* `label` - The field name to be displayed in the rendered form
* `required` - Indicates whether the field is mandatory (all fields are required by default)
* `widget` - The class of form widget to use (see the [Django documentation](https://docs.djangoproject.com/en/stable/ref/forms/widgets/))

### `StringVar`

Stores a string of characters (i.e. text). Options include:

* `min_length` - Minimum number of characters
* `max_length` - Maximum number of characters
* `regex` - A regular expression against which the provided value must match

Note that `min_length` and `max_length` can be set to the same number to effect a fixed-length field.

### `TextVar`

Arbitrary text of any length. Renders as a multi-line text input field.

### `JSONVar`

+++ 2.1.0

Accepts JSON-formatted data of any length. Renders as a multi-line text input field. The variable passed to `run()` method on the Job has been serialized to the appropriate Python objects.

```python
from nautobot.apps.jobs import Job, JSONVar

class ExampleJSONVarJob(Job):
    var1 = JSONVar(
        description="Provide a JSON object with a 'key1' field.",
    )

    def run(self, var1):
        # Example input: {"key1": "value1"}
        if "key1" in var1:
            self.logger.info("The value of key1 is: %s", var1["key1"])
        else:
            self.logger.error("Missing required key: key1")
```

This Job uses a JSONVar to accept a structured input from the user. For example, the user might submit `{"key1": "value1"}`. Nautobot first validates that the input is valid JSON, then automatically deserializes it into a Python dictionary. Inside the Job, you can access the dictionary directly — in this case, logging the value of key1 or raising an error if it’s missing. This is a simple way to demonstrate structured input, useful for things like configuration blobs or external API payloads, without needing to manually parse the JSON yourself.

### `IntegerVar`

Stores a numeric integer. Options include:

* `min_value` - Minimum value
* `max_value` - Maximum value

### `BooleanVar`

A true/false flag. This field has no options beyond the defaults listed above.

### `DryRunVar`

A true/false flag with special handling for Jobs that require approval. If `dryrun = DryRunVar()` is declared on a Job class, approval may be bypassed if `dryrun` is set to `True` on Job execution.

### `ChoiceVar`

A set of choices from which the user can select one.

* `choices` - A list of `(value, label)` tuples representing the available choices. For example:

```python
from nautobot.apps.jobs import Job, ChoiceVar, register_jobs

DIRECTIONS = (
    ("n", "North"),
    ("s", "South"),
    ("e", "East"),
    ("w", "West"),
)

class CompassJob(Job):
    direction = ChoiceVar(
        choices=DIRECTIONS,
        description="Choose a cardinal direction."
    )

    def run(self, *, direction):
        self.logger.info("You chose to go: %s", dict(DIRECTIONS)[direction])

register_jobs(CompassJob)
```

This example uses a `ChoiceVar` to let the user select one option from a list of predefined values. When the Job runs, the selected value (e.g., `"n"`) is passed to the `run()` method. The Job then looks up the human-readable label (`"North"`) and logs it. This pattern is useful when you want to limit input to a safe, predictable set of options.

### `MultiChoiceVar`

Similar to `ChoiceVar`, but allows for the selection of multiple choices.

### `ObjectVar`

A `ObjectVar` allows users to select a single Nautobot object (such as a device, interface, or location) via the UI or API. It accepts several options to customize its behavior, from simple selections to dynamic filters and nested fields.

You can customize how objects appear in the selection dropdown and what subset of records are made available using the following arguments:

- `model`: The Django model class to query (e.g., `Device`, `Location`, `IPAddress`).
- `display_field`: The model attribute to display for each object in the UI dropdown. Defaults to the object’s `display` property. You can specify any valid attribute, including nested fields (e.g., `vlan_group.name`) or computed fields (e.g., `computed_fields.mycustomfield`).
- `query_params`: A dictionary of query parameters used to filter the available options. These follow the same structure as the Nautobot REST API.
- `null_option`: An optional label that represents an empty selection.

#### Basic Usage

```python
from nautobot.apps.jobs import Job, ObjectVar, register_jobs
from nautobot.dcim.models import Device

class ChooseDevice(Job):
    device = ObjectVar(
        model=Device,
        description="Pick a device to validate."
    )

    def run(self, *, device):
        self.logger.info("You selected the device: %s", device)

register_jobs(ChooseDevice)
```

This Job lets a user select a `Device` object from a dropdown. That selected object is passed as an argument to the `run()` method. This pattern is useful for Jobs that operate on a specific record from Nautobot.

#### Customizing Display Field

By default, Nautobot will show each object's `display` field in the dropdown. To show a different field—such as a hostname, IP, or a related model’s attribute—you can override it using `display_field`.

```python
device_ip = ObjectVar(
    model=IPAddress,
    display_field="dns_name",  # Instead of the default "address" or "display"
)
```

You can also use dot notation to reference nested or related fields, such as a VLAN's group name:

```python
vlan = ObjectVar(
    model=VLAN,
    display_field="vlan_group.name",
    query_params={"depth": 1}  # Ensures nested objects are populated
)
```

In the example above, [`"depth": 1`](../../user-guide/platform-functionality/rest-api/overview.md#depth-query-parameter) was needed to influence REST API to include details of the associated records.


#### Using Computed Fields

Another example of using the nested reference would be to access [computed fields](../../user-guide/platform-functionality/computedfield.md) of the model. Nautobot supports selecting computed fields as part of the `display_field`, provided the API query includes them:

```python
interface = ObjectVar(
    model=Interface,
    display_field="computed_fields.mycustomfield",
    query_params={"include": "computed_fields"}
)
```

This allows users to see custom-calculated values—like interface capacity scores or normalized labels—in the dropdown UI. It's especially useful when default display fields aren't meaningful enough on their own for selection.

To limit the selections available within the list, additional query parameters can be passed as the `query_params` dictionary. For example, to show only devices with an "active" status:

```python
device = ObjectVar(
    model=Device,
    query_params={
        'status': 'active'
    }
)
```

#### Filtering Options with `query_params`

Use `query_params` to filter which objects appear in the dropdown. For example, only show devices that are “active”:

```python
device = ObjectVar(
    model=Device,
    query_params={"status": "active"}
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

### `MultiObjectVar`

Similar to `ObjectVar`, but allows for the selection of multiple objects.

### `FileVar`

An uploaded file provided via `FileVar` is passed to the Job's `run()` method as an in-memory file-like object, typically an `InMemoryUploadedFile`. These are temporary and exist only for the duration of the Job execution—they are not saved automatically.

The example below shows how to use `FileVar` to upload a CSV file, decode its contents, and process each row with Python’s `csv.DictReader`. This pattern is useful when working with structured input formats such as device inventories, IP assignments, or user data.

If you want to retain output from a Job (e.g. processed data or error logs), you can use `self.create_file()` to save and expose results via the JobResult detail page.

```python
import csv
from nautobot.apps.jobs import Job, FileVar, register_jobs

class ReadCSVJob(Job):
    class Meta:
        name = "Read CSV Upload"

    input_file = FileVar(description="Upload a CSV file with hostname,ip_address columns")

    def run(self, *, input_file):
        decoded_file = input_file.read().decode("utf-8").splitlines()
        reader = csv.DictReader(decoded_file)
        for row in reader:
            self.logger.info("Hostname: %s, IP Address: %s", row["hostname"], row["ip_address"])

register_jobs(ReadCSVJob)
```

!!! note
    Files provided via `FileVar` must be read and processed during the `run()` method. If needed, use `self.create_file()` to persist any output for download after execution.

### `IPAddressVar`

An IPv4 or IPv6 address, without a mask. Returns a `netaddr.IPAddress` object.

### `IPAddressWithMaskVar`

An IPv4 or IPv6 address with a mask. Returns a `netaddr.IPNetwork` object which includes the mask.

### `IPNetworkVar`

An IPv4 or IPv6 network with a mask. Returns a `netaddr.IPNetwork` object. Two attributes are available to validate the provided mask:

* `min_prefix_length` - Minimum length of the mask
* `max_prefix_length` - Maximum length of the mask

## Special Methods

Special methods allow you to manage the execution lifecycle of a Job, providing hooks to run code at critical points such as initialization, successful execution, or error handling. Implementing these methods can improve robustness, debugging, and reliability of Jobs.

Nautobot Jobs when executed will be instantiated by Nautobot, then Nautobot will call in order the special API methods `before_start()`, `run()`, `on_success()`/`on_failure()`, and `after_return()`. You must implement the `run()` method; the other methods have default implementations that do nothing.

As Jobs are Python classes, you are of course free to define any number of other helper methods or functions that you call yourself from within any of the above special methods, but the above are the only ones that will be automatically called.

--- 2.0.0 "Removal of `test` and `post_run` special methods"
    The NetBox backwards compatible `test_*()` and `post_run()` special methods have been removed.

### The `before_start()` Method

The `before_start()` method may optionally be implemented to perform any appropriate Job-specific setup before the `run()` method is called. It has the signature `before_start(self, task_id, args, kwargs)` for historical reasons; the `task_id` parameter will always be identical to `self.request.id`, the `args` parameter will generally be empty, and any user-specified variables passed into the Job execution will be present in the `kwargs` parameter.

The return value from `before_start()` is ignored, but if it raises any exception, the Job result status will be marked as `FAILURE` and `run()` will not be called.


### The `create_file()` Method

+++ 2.1.0

Jobs can generate output files during execution using the `create_file()` method. These files are saved and made available to the user from the JobResult detail view’s **Advanced** tab or via the REST API.

This is useful when you want to:

- Generate downloadable reports
- Return structured outputs (e.g. CSV, JSON)
- Provide a summary or log of what the Job did

```python
from nautobot.apps.jobs import Job, register_jobs

class ExportText(Job):
    class Meta:
        name = "Export Text File"

    def run(self):
        self.create_file("output.txt", "Export completed successfully.")
        self.logger.info("File has been created for download.")

register_jobs(ExportText)
```

The `create_file()` method accepts a filename and file contents (as `str` or `bytes`). Files are saved alongside the JobResult and remain available until the JobResult is deleted.

!!! note
    The maximum file size and storage backend for output files are controlled by the [`JOB_CREATE_FILE_MAX_SIZE`](../../user-guide/administration/configuration/settings.md#job_create_file_max_size) and [`JOB_FILE_IO_STORAGE`](../../user-guide/administration/configuration/settings.md#job_file_io_storage) settings.

### The `run()` Method

The `run()` method is the core of every Job and is required. It receives user-supplied inputs (defined as variables on the class) as keyword arguments. Inside this method, you define the logic that the Job will execute—such as querying data, applying changes, or interacting with external systems. The method can return a value, which will be saved in the JobResult and displayed in the UI and API.

Here’s a basic structure:

```python
from nautobot.apps.jobs import Job, StringVar

class SimpleGreetingJob(Job):
    name_input = StringVar(description="Who should we greet?")

    def run(self, *, name_input):
        self.logger.info("Hello, %s!", name_input)

register_jobs(SimpleGreetingJob)
```

Again, defining user variables is totally optional; you may create a Job with a `run()` method with only the `self` argument if no user input is needed.

!!! warning "Use `validated_save()` where applicable"
    When writing Jobs that create and manipulate data it is recommended to make use of the `validated_save()` convenience method which exists on all core models. This method saves the instance data but first enforces model validation logic. Simply calling `save()` on the model instance **does not** enforce validation automatically and may lead to bad data. See the development [best practices](../core/best-practices.md).

!!! warning "Be cautious around bulk operations"
    The Django ORM provides methods to create/edit many objects at once, namely `bulk_create()` and `update()`. These are best avoided in most cases as they bypass a model's built-in validation and can easily lead to database corruption if not used carefully.

#### Returning and Failing from `run()`

The return value of the `run()` method is saved to the JobResult and is viewable in both the Nautobot UI and API. If `run()` completes without error, the Job is automatically marked as **SUCCESS**.

There are two ways to explicitly mark a Job as failed:

- Call `self.fail("message")` to mark the Job as **FAILURE** without raising an exception or halting execution.
- Raise an exception to stop the Job immediately. Nautobot will capture the error and traceback in the JobResult.

Calling `self.fail()` is useful for validation or soft failures that don’t require a hard stop.

```python
from nautobot.apps.jobs import Job, StringVar, register_jobs

class CheckOccasion(Job):
    occasion = StringVar(description="Enter an occasion")

    def run(self, *, occasion):
        if not occasion.startswith("Taco"):
            self.logger.error("Occasion must begin with 'Taco'")
            raise Exception("Input validation failed.")

        if not occasion.endswith("Tuesday"):
            self.fail("It's supposed to be Tuesday!")  # Marks job as FAILURE without traceback

        self.logger.info("Perfect! Today is %s", occasion)
        return occasion

register_jobs(CheckOccasion)
```

In this example, if the `occasion` input doesn’t start with “Taco”, an exception is raised and the Job fails immediately. If the input ends incorrectly (but started correctly), the Job continues but is still marked as failed using `self.fail()`. Otherwise, the Job logs a success message and completes normally, returning the value to the JobResult.

### The `on_success()` Method

If both `before_start()` and `run()` are successful, the `on_success()` method will be called next, if implemented. It has the signature `on_success(self, retval, task_id, args, kwargs)`; as with `before_start()` the `task_id` and `args` parameters can generally be ignored, while `retval` is the return value from `run()`, and `kwargs` will contain the user-specified variables passed into the Job execution.

### The `on_failure()` Method

If either `before_start()` or `run()` raises any unhandled exception, or reports a failure overall through `fail()`, the `on_failure()` method will be called next, if implemented. It has the signature `on_failure(self, exc, task_id, args, kwargs, einfo)`; of these parameters, the `exc` will contain the exception that was raised (if any) or the return value from `before_start()` or `run()` (otherwise), and `kwargs` will contain the user-specified variables passed into the Job.

### The `after_return()` Method

Regardless of the overall Job execution success or failure, the `after_return()` method will be called after `on_success()` or `on_failure()`. It has the signature `after_return(self, status, retval, task_id, args, kwargs, einfo)`; the `status` will indicate success or failure (using the `JobResultStatusChoices` enum), `retval` is *either* the return value from `run()` or the exception raised, and once again `kwargs` contains the user variables.


## Reserved Names: Avoiding Collisions with Job Internals

When writing Jobs, it's important to avoid reusing internal attribute or method names from the `Job` class. Doing so can interfere with how Jobs are registered, rendered, or executed. The following table outlines reserved names you **should not** use for variable names or method overrides.

There are many attributes and methods of the Job class that serve as reserved names. You must be careful when implementing custom methods or defining the user input [variables](#variables) for your Job that you do not inadvertently "step on" one of these reserved attributes causing unexpected behavior or errors.

!!! warning "Don't override built-in attributes"
    A common mistake is redefining the reserved `name` attribute as a user input variable. This overrides the Job’s display name and may prevent the Job from running correctly.

As of Nautobot 2.4.0, the current list of reserved names (not including low-level Python built-ins such as `__dict__` or `__str__` includes:

| Reserved Name             | Purpose                                                                 |
|---------------------------|-------------------------------------------------------------------------|
| `after_return`            | [special method](#the-after_return-method)                              |
| `approval_required`       | [metadata property](#approval_required)                                 |
| `as_form`                 | class method                                                            |
| `as_form_class`           | class method                                                            |
| `before_start`            | [special method](#the-before_start-method)                              |
| `celery_kwargs`           | property                                                                |
| `class_path`              | class property                                                          |
| `class_path_dotted`       | deprecated class property                                               |
| `class_path_js_escaped`   | class property                                                          |
| `create_file`             | [helper method](#the-create_file-method)                                |
| `description`             | [metadata property](#description)                                      |
| `description_first_line`  | [metadata property](#description)                                      |
| `deserialize_data`        | internal class method                                                   |
| `dryrun_default`          | [metadata property](#dryrun_default)                                   |
| `fail`                    | [helper method](#returning-and-failing-from-run)                        |
| `field_order`             | [metadata property](#field_order)                                      |
| `file_path`               | deprecated class property                                               |
| `grouping`                | [module metadata property](#name-grouping)                              |
| `has_sensitive_variables` | [metadata property](#has_sensitive_variables)                           |
| `hidden`                  | [metadata property](#hidden)                                           |
| `is_singleton`            | [metadata property](#is_singleton)                                     |
| `job_model`               | property                                                                |
| `job_result`              | property                                                                |
| `load_json`               | [helper method](./job-patterns.md#reading-static-data-from-files)              |
| `load_yaml`               | [helper method](./job-patterns.md#reading-static-data-from-files)              |
| `name`                    | [metadata property](#name)                                              |
| `on_failure`              | [special method](#the-on_failure-method)                                |
| `on_retry`                | reserved as a future special method *(not present)* |
| `on_success`              | [special method](#the-on_success-method)                                |
| `prepare_job_kwargs`      | internal class method                                                   |
| `properties_dict`         | class property                                                          |
| `read_only`               | [metadata property](#read_only)                                        |
| `registered_name`         | deprecated class property                                               |
| `run`                     | [special method](#the-run-method)                                       |
| `serialize_data`          | internal method                                                         |
| `soft_time_limit`         | [metadata property](#soft_time_limit)                                  |
| `supports_dryrun`         | class property                                                          |
| `task_queues`             | [metadata property](#task_queues)                                      |
| `template_name`           | [metadata property](#template_name)                                    |
| `time_limit`              | [metadata property](#time_limit)                                      |
| `user`                    | property                                                                |
| `validate_data`           | internal class method                                                   |
 