# Jobs

Familiarity with the basic concepts of [Jobs](../../user-guide/platform-functionality/jobs/index.md), especially the distinction between Job classes (Python code) and Job records (Nautobot database records), is recommended before authoring your first Job.

??? tip "More about Job class source code loading"
    From a development standpoint, it's especially important to understand that the Job database record never stores the Job class code. It only describes the **existence** of a Job class. The actual Job class source code is loaded into memory only.

    As an implementation detail in Nautobot 2.2.3 and later, all known Job **classes** are cached in the [application registry](../core/application-registry.md#jobs), which is refreshed at various times including Nautobot application startup and immediately prior to actually executing any given Job by a worker. This implementation detail should not be relied on directly; instead you should always use the `get_job()` and/or `get_jobs()` APIs to obtain a Job class when needed.

## Migrating Jobs from v1 to v2

See [Migrating Jobs From Nautobot v1](migration/from-v1.md) for more information on how to migrate your existing Jobs to Nautobot v2.

## Installing Jobs

Jobs may be installed in one of three ways:

* Manually installed as files in the [`JOBS_ROOT`](../../user-guide/administration/configuration/settings.md#jobs_root) path (which defaults to `$NAUTOBOT_ROOT/jobs/`).
    * Python files and subdirectories containing Python files will be dynamically loaded at Nautobot startup in order to discover and register available Job classes. For example, a Job class named `MyJobClass` in `$JOBS_ROOT/my_job.py` will be loaded into Nautobot as `my_job.MyJobClass`.
    * All Python modules in this directory are imported by Nautobot and all worker processes at startup. If you have a `custom_jobs.py` and a `custom_jobs_module/__init__.py` file in your `JOBS_ROOT`, both of these files will be imported at startup.
* Imported from an external [Git repository](../../user-guide/platform-functionality/gitrepository.md#jobs).
    * Git repositories are loaded into the module namespace of the `GitRepository.slug` value at startup. For example, if your `slug` value is `my_git_jobs` your Jobs will be loaded into Python as `my_git_jobs.jobs.MyJobClass`.
    * All git repositories providing Jobs must include a `__init__.py` file at the root of the repository.
    * Nautobot and all worker processes will import the git repository's `jobs` module at startup so a `jobs.py` or `jobs/__init__.py` file must exist in the root of the repository.
* Packaged as part of an [App](../apps/api/platform-features/jobs.md).
    * Jobs installed this way are part of the App's Python module and can import code from elsewhere in the App or even have dependencies on other packages, if needed, via the standard Python packaging mechanisms.

In any case, each module holds one or more Job classes (Python classes), each of which serves a specific purpose. The logic of each Job can be split into a number of distinct methods, each of which performs a discrete portion of the overall Job logic.

For example, we can create a module named `device_jobs.py` to hold all of our Jobs which pertain to devices in Nautobot. Within that module, we might define several Jobs. Each Job is defined as a Python class inheriting from `nautobot.apps.jobs.Job`, which provides the base functionality needed to accept user input and log activity.

+/- 2.0.0 "`register_jobs()` must be called"
    All Job classes that are intended to be runnable must now be registered by a call to `nautobot.apps.jobs.register_jobs()` on module import. This allows for a module to, if desired, define "abstract" base Job classes that are defined in code but are not registered (and therefore are not runnable in Nautobot). The `register_jobs` method accepts one or more Job classes as arguments.

## Writing Jobs

### Introduction to Writing Jobs

!!! warning
    Make sure your Job subclasses inherit from `nautobot.apps.jobs.Job` and *not* from `nautobot.extras.models.Job` instead; if you mistakenly inherit from the latter, Django will think you want to define a new database model!

The most basic structure of a Python file providing one or more Jobs is as follows:

```python
from nautobot.apps import jobs

name = "My Group Of Jobs"  # optional, but recommended to define a grouping name

class MyNewJob(jobs.Job):
    class Meta:
        # metadata attributes go here
        name = "My New Job"
        # ... etc.

    # input variable definitions go here
    some_text_input = jobs.StringVar(...)
    # ... etc.

    def run(self, *, some_text_input, ...):
        # code to execute when the Job is run goes here
        self.logger.info("some_text_input: %s", some_text_input)

jobs.register_jobs(MyNewJob)
```

Each Job class will implement some or all of the following components:

* [Module](#module-metadata-attributes) and class [metadata attributes](#class-metadata-attributes), configuring the system-level behavior of the Job and providing for documentation and discoverability by users.
* A set of [variables](#variables) for user input via the Nautobot UI or API.
* The [`run()` method](#the-run-method), which is the only **required** attribute on a Job class and receives the user input values as keyword arguments.
* Optionally, any of the special methods [`before_start()`](#the-before_start-method), [`on_success()`](#the-on_success-method), [`on_failure()`](#the-on_failure-method), and/or [`after_return()`](#the-after_return-method).

It's important to understand that Jobs execute on the server asynchronously as background tasks; they log messages and report their status to the database by updating [`JobResult`](../../user-guide/platform-functionality/jobs/models.md#job-results) records and creating [`JobLogEntry`](../../user-guide/platform-functionality/jobs/models.md#job-log-entry) records.

!!! note "About detection of changes while developing a Job"
    When actively developing a Job utilizing a development environment it's important to understand that the "automatically reload when code changes are detected" debugging functionality provided by `nautobot-server runserver` does **not** automatically restart the Celery `worker` process when code changes are made; therefore, it is required to restart the `worker` after each update to your Job source code or else it will continue to run the version of the Job code that was present when it first started. In the Nautobot core development environment, we use `watchmedo auto-restart` as a helper tool to auto-restart the workers as well on code changes; you may wish to configure your local development environment similarly for convenience.

    Additionally, as of Nautobot 1.3, the Job database records corresponding to installed Jobs are *not* automatically refreshed when the development server auto-restarts. If you make changes to any of the class and module metadata attributes described in the following sections, the database will be refreshed to reflect these changes only after running `nautobot-server migrate` or `nautobot-server post_upgrade` (recommended) or if you manually edit a Job database record to force it to be refreshed. The exception here is Git-repository-provided Jobs; resyncing the Git repository through Nautobot will also trigger a refresh of the Job records corresponding to this repository's contents.

### Job Registration

+/- 2.0.0 "`register_jobs()` is now required"

All Job classes, including `JobHookReceiver` and `JobButtonReceiver` classes must be registered at **import time** using the `nautobot.apps.jobs.register_jobs` method. This method accepts one or more Job classes as arguments. You must account for how your Jobs are imported when deciding where to call this method.

#### Registering Jobs in `JOBS_ROOT` or Git Repositories

Only top level module names within `JOBS_ROOT` are imported by Nautobot at runtime. This means that if you're using submodules, you need to ensure that your Jobs are either registered in your top level `__init__.py` or that this file imports your submodules where the Jobs are registered:

```py title="$JOBS_ROOT/my_jobs/__init__.py"
from . import my_job_module
```

```py title="$JOBS_ROOT/my_jobs/my_job_module.py"
from nautobot.apps.jobs import Job, register_jobs

class MyJob(Job):
    ...

register_jobs(MyJob)
```

Similarly, only the `jobs` module is loaded from Git repositories. If you're using submodules, you need to ensure that your Jobs are either registered in the repository's `jobs/__init__.py` or that this file imports your submodules where the Jobs are registered.

If not using submodules, you should register your Job in the file where it is defined.

Examples of the different directory structures when registering Jobs in Git repositories:

!!! note "`__init__.py`"
    Take note of the `__init__.py` at the root of the repository.  This is required to register Jobs in a Git repository.

``` title="jobs.py"
.
├── __init__.py
└── jobs.py
```

``` title="submodule"
.
├── __init__.py
└── jobs
    ├── __init__.py
    └── my_job_module.py
```

#### Registering Jobs in an App

Apps should register Jobs in the module defined in their [`NautobotAppConfig.jobs`](../apps/api/nautobot-app-config.md#nautobotappconfig-code-location-attributes) property. This defaults to the `jobs` module of the App.

### Reserved Attribute Names

There are many attributes and methods of the Job class that serve as reserved names. You must be careful when implementing custom methods or defining the user input [variables](#variables) for your Job that you do not inadvertently "step on" one of these reserved attributes causing unexpected behavior or errors.

!!! example
    One classic pitfall here is the the reserved `name` metadata attribute - if you attempt to redefine `name` as a user input variable, your Job will not work.

As of Nautobot 2.4.0, the current list of reserved names (not including low-level Python built-ins such as `__dict__` or `__str__` includes:

| Reserved Name             | Purpose                                                 |
| ------------------------- | ------------------------------------------------------- |
| `after_return`            | [special method](#special-methods)                      |
| `approval_required`       | [metadata property](#approval_required)                 |
| `as_form`                 | class method                                            |
| `as_form_class`           | class method                                            |
| `before_start`            | [special method](#special-methods)                      |
| `celery_kwargs`           | property                                                |
| `class_path`              | class property                                          |
| `class_path_dotted`       | deprecated class property                               |
| `class_path_js_escaped`   | class property                                          |
| `create_file`             | [helper method](#file-output)                           |
| `description`             | [metadata property](#description)                       |
| `description_first_line`  | [metadata property](#description)                       |
| `deserialize_data`        | internal class method                                   |
| `dryrun_default`          | [metadata property](#dryrun_default)                    |
| `file_path`               | deprecated class property                               |
| `field_order`             | [metadata property](#field_order)                       |
| `grouping`                | [module metadata property](#module-metadata-attributes) |
| `has_sensitive_variables` | [metadata property](#has_sensitive_variables)           |
| `hidden`                  | [metadata property](#hidden)                            |
| `is_singleton`            | [metadata property](#is_singleton)                      |
| `job_model`               | property                                                |
| `job_result`              | property                                                |
| `load_json`               | [helper method](#reading-data-from-files)               |
| `load_yaml`               | [helper method](#reading-data-from-files)               |
| `name`                    | [metadata property](#name)                              |
| `on_failure`              | [special method](#special-methods)                      |
| `on_retry`                | reserved as a future [special method](#special-methods) |
| `on_success`              | [special method](#special-methods)                      |
| `prepare_job_kwargs`      | internal class method                                   |
| `properties_dict`         | class property                                          |
| `read_only`               | [metadata property](#read_only)                         |
| `registered_name`         | deprecated class property                               |
| `run`                     | [special method](#special-methods)                      |
| `serialize_data`          | internal method                                         |
| `soft_time_limit`         | [metadata property](#soft_time_limit)                   |
| `supports_dryrun`         | class property                                          |
| `task_queues`             | [metadata property](#task_queues)                       |
| `template_name`           | [metadata property](#template_name)                     |
| `time_limit`              | [metadata property](#time_limit)                        |
| `user`                    | property                                                |
| `validate_data`           | internal class method                                   |

### Module Metadata Attributes

#### `name` (Grouping)

You can define a global constant called `name` within a job module (the Python file which contains one or more Job classes) to set the default grouping under which the Jobs in this module will be displayed in the Nautobot UI. If this value is not defined, the module's file name will be used. This "grouping" value may also be defined or overridden when editing Job records in the database.

!!! note
    In some UI elements and API endpoints, the module file name is displayed in addition to or in place of this attribute, so even if defining this attribute, you should still choose an appropriately explanatory file name as well.

### Class Metadata Attributes

Job-specific attributes may be defined under a class named `Meta` within each Job class you implement. All of these are optional, but encouraged.

#### `name`

This is the human-friendly name of your Job, as will be displayed in the Nautobot UI. If not set, the class name will be used.

!!! note
    In some UI elements and API endpoints, the class name is displayed in addition to or in place of this attribute, so even if defining this attribute, you should still choose an appropriately explanatory class name as well.

#### `description`

An optional human-friendly description of what this Job does.
This can accept either plain text, Markdown-formatted text, or [a limited subset of HTML](../../user-guide/platform-functionality/template-filters.md#render_markdown). It can also be multiple lines:

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

#### `approval_required`

Default: `False`

A boolean that will mark this Job as requiring approval from another user to be run. For more details on approvals, [please refer to the section on scheduling and approvals](../../user-guide/platform-functionality/jobs/job-scheduling-and-approvals.md).

#### `dryrun_default`

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

#### `field_order`

Default: `[]`

A list of strings (field names) representing the order your Job [variables](#variables) should be rendered as form fields in the Job submission UI. If not defined, the variables will be listed in order of their definition in the code. If variables are defined on a parent class and no field order is defined, the parent class variables will appear before the subclass variables.

#### `has_sensitive_variables`

+++ 1.3.10

Default: `True`

Unless set to False, it prevents the Job's input parameters from being saved to the database. This defaults to True so as to protect against inadvertent database exposure of input parameters that may include sensitive data such as passwords or other user credentials. Review whether each Job's inputs contain any such variables before setting this to False; if a Job *does* contain sensitive inputs, if possible you should consider whether the Job could be re-implemented using Nautobot's [`Secrets`](../../user-guide/platform-functionality/secret.md) feature as a way to ensure that the sensitive data is not directly provided as a Job variable at all.

Important notes about Jobs with sensitive variables:

* Such Jobs cannot be scheduled to run in the future or on a recurring schedule (as Scheduled Jobs must by necessity store their variables in the database for future reference).
* Jobs with sensitive variables cannot be marked as requiring approval (as Jobs pending approval must store their variables in the database until approved).

#### `hidden`

Default: `False`

A Boolean that if set to `True` prevents the Job from being displayed by default in the list of Jobs in the Nautobot UI.

Since the Job execution framework is designed to be generic, there may be several technical Jobs defined by users which interact with or are invoked by external systems. In such cases, these Jobs are not meant to be executed by a human and likely do not make sense to expose to end users for execution, and thus having them exposed in the UI at all is extraneous.

Important notes about hidden Jobs:

* This is merely hiding them by default from the web interface. It is NOT a security feature.
* In the Jobs list view it is possible to filter to "Hidden: (no selection)" or even "Hidden: Yes" to list the hidden Jobs.
* All Job UI and REST API endpoints still exist for hidden Jobs and can be accessed by any user who is aware of their existence.
* Hidden Jobs can still be executed through the UI or the REST API given the appropriate URL.
* Results for hidden Jobs will still appear in the Job Results list after they are run.

#### `is_singleton`

+++ 2.4.0

Default: `False`
A Boolean that if set to `True` prevents the job from running twice simultaneously.

Any duplicate job instances will error out with a singleton-specific error message.

Important notes about singleton jobs:

* The singleton functionality is implemented with a Redis key set to timeout either on the hard time out of the job or whenever the job terminates.
    * Therefore, a restart of Redis will wipe the singleton locks
* A checkbox on the job run form makes it possible to force the singleton lock to be overridden. This makes it possible to recover from failure scenarios such as the original singleton job being stopped before it can unset the lock.

#### `read_only`

+++ 1.1.0

+/- 2.0.0 "No automatic functionality"
    The `read_only` flag no longer changes the behavior of Nautobot core and is up to the Job author to decide whether their Job should be considered read only.

Default: `False`

A boolean that can be set by the Job author to indicate that the Job does not make any changes to the environment. What behavior makes each Job "read only" is up to the individual Job author to decide. Note that user input may still be optionally collected with read-only Jobs via Job variables, as described below.

#### `soft_time_limit`

+++ 1.3.0

An int or float value, in seconds, which can be used to override the default [soft time limit](../../user-guide/administration/configuration/settings.md#celery_task_soft_time_limit) for a Job task to complete.

The `celery.exceptions.SoftTimeLimitExceeded` exception will be raised when this soft time limit is exceeded. The Job task can catch this to clean up before the [hard time limit](../../user-guide/administration/configuration/settings.md#celery_task_time_limit) (10 minutes by default) is reached:

```python
from celery.exceptions import SoftTimeLimitExceeded
from nautobot.apps.jobs import Job

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

A list of Job Queue names that the Job can be routed to. An empty list will default to only allowing the user to select the [default Celery queue](../../user-guide/administration/configuration/settings.md#celery_task_default_queue) (`default` unless changed by an administrator). The queue specified in the Job's `default_job_queue` will be used if a queue is not specified in a Job run API call.

+/- 2.4.0 "Changed default queue selection"
    As a result of the addition of Job Queues, the default queue when running a Job without explicitly selecting a queue is now the job queue specified in the `default_job_queue` field on the Job model. `default_job_queue` fields for any existing Job instances are automatically populated with the name of the first entry in `task_queues` list of the Job class. When `task_queues` list on the Job class is empty, the corresponding Job instance's `default_job_queue` will be the job queue with the name provided by `settings.CELERY_TASK_DEFAULT_QUEUE`. You can also override the initial `default_job_queue` by setting `default_job_queue_override` to True and assign the field with a different Job Queue instance.

!!! note
    A worker must be listening on the requested queue or the Job will not run. See the documentation on [task queues](../../user-guide/administration/guides/celery-queues.md) for more information.

#### `template_name`

+++ 1.4.0

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

#### `time_limit`

+++ 1.3.0

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

### Variables

Variables allow your Job to accept user input via the Nautobot UI, but they are optional; if your Job does not require any user input, there is no need to define any variables. Conversely, if you are making use of user input in your Job, you *must* also implement the `run()` method, as it is the only entry point to your Job that has visibility into the variable values provided by the user.

```python
from nautobot.apps.jobs import Job, StringVar, IntegerVar, ObjectVar

class CreateDevices(Job):
    var1 = StringVar(...)
    var2 = IntegerVar(...)
    var3 = ObjectVar(...)

    def run(self, var1, var2, var3):
        ...
```

The remainder of this section documents the various supported variable types and how to make use of them.

#### Default Variable Options

All Job variables support the following default options:

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

#### `JSONVar`

+++ 2.1.0

Accepts JSON-formatted data of any length. Renders as a multi-line text input field. The variable passed to `run()` method on the Job has been serialized to the appropriate Python objects.

```python
class ExampleJSONVarJob(Job):
    var1 = JSONVar()

    def run(self, var1):
        # var1 form data equals '{"key1": "value1"}'
        self.logger.info("The value of key1 is: %s", var1["key1"])
```

In the above example `{"key1": "value1"}` is provided to the Job form, on submission first the field is validated to be JSON-formatted data then is serialized and passed to the `run()` method as a dictionary without any need for the Job developer to post-process the variable into a Python dictionary.

#### `IntegerVar`

Stores a numeric integer. Options include:

* `min_value` - Minimum value
* `max_value` - Maximum value

#### `BooleanVar`

A true/false flag. This field has no options beyond the defaults listed above.

#### `DryRunVar`

A true/false flag with special handling for Jobs that require approval. If `dryrun = DryRunVar()` is declared on a Job class, approval may be bypassed if `dryrun` is set to `True` on Job execution.

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

Additionally, the `.` notation can be used to reference nested fields:

```python
device_type = ObjectVar(
    model=VLAN,
    display_field="vlan_group.name",
    query_params={
        "depth": 1
    },
)
```

In the example above, [`"depth": 1`](../../user-guide/platform-functionality/rest-api/overview.md#depth-query-parameter) was needed to influence REST API to include details of the associated records.
Another example of using the nested reference would be to access [computed fields](../../user-guide/platform-functionality/computedfield.md) of the model:

```python
device_type = ObjectVar(
    model=Interface,
    display_field="computed_fields.mycustomfield",
    query_params={
        "include": "computed_fields"
    },
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

An uploaded file. Note that uploaded files are present in memory only for the duration of the Job's execution: They will not be automatically saved for future use. The Job is responsible for writing file contents to disk where necessary.

#### `IPAddressVar`

An IPv4 or IPv6 address, without a mask. Returns a `netaddr.IPAddress` object.

#### `IPAddressWithMaskVar`

An IPv4 or IPv6 address with a mask. Returns a `netaddr.IPNetwork` object which includes the mask.

#### `IPNetworkVar`

An IPv4 or IPv6 network with a mask. Returns a `netaddr.IPNetwork` object. Two attributes are available to validate the provided mask:

* `min_prefix_length` - Minimum length of the mask
* `max_prefix_length` - Maximum length of the mask

### Special Methods

Nautobot Jobs when executed will be instantiated by Nautobot, then Nautobot will call in order the special API methods `before_start()`, `run()`, `on_success()`/`on_failure()`, and `after_return()`. You must implement the `run()` method; the other methods have default implementations that do nothing.

As Jobs are Python classes, you are of course free to define any number of other helper methods or functions that you call yourself from within any of the above special methods, but the above are the only ones that will be automatically called.

--- 2.0.0 "Removal of `test` and `post_run` special methods"
    The NetBox backwards compatible `test_*()` and `post_run()` special methods have been removed.

#### The `before_start()` Method

The `before_start()` method may optionally be implemented to perform any appropriate Job-specific setup before the `run()` method is called. It has the signature `before_start(self, task_id, args, kwargs)` for historical reasons; the `task_id` parameter will always be identical to `self.request.id`, the `args` parameter will generally be empty, and any user-specified variables passed into the Job execution will be present in the `kwargs` parameter.

The return value from `before_start()` is ignored, but if it raises any exception, the Job execution will be marked as a failure and `run()` will not be called.

#### The `run()` Method

The `run()` method is the primary worker of any Job, and must be implemented. After the `self` argument, it should accept keyword arguments for any variables defined on the Job:

```python
from nautobot.apps.jobs import Job, StringVar, IntegerVar, ObjectVar

class CreateDevices(Job):
    var1 = StringVar(...)
    var2 = IntegerVar(...)
    var3 = ObjectVar(...)

    def run(self, *, var1, var2, var3):
        ...
```

Again, defining user variables is totally optional; you may create a Job with a `run()` method with only the `self` argument if no user input is needed.

!!! warning "Use `validated_save()` where applicable"
    When writing Jobs that create and manipulate data it is recommended to make use of the `validated_save()` convenience method which exists on all core models. This method saves the instance data but first enforces model validation logic. Simply calling `save()` on the model instance **does not** enforce validation automatically and may lead to bad data. See the development [best practices](../core/best-practices.md).

!!! warning "Be cautious around bulk operations"
    The Django ORM provides methods to create/edit many objects at once, namely `bulk_create()` and `update()`. These are best avoided in most cases as they bypass a model's built-in validation and can easily lead to database corruption if not used carefully.

If `run()` returns any value (even the implicit `None`), the Job execution will be marked as a success and the returned value will be stored in the associated JobResult database record. Conversely, if `run()` raises any exception, the Job execution will be marked as a failure and the traceback will be stored in the JobResult.

#### The `on_success()` Method

If both `before_start()` and `run()` are successful, the `on_success()` method will be called next, if implemented. It has the signature `on_success(self, retval, task_id, args, kwargs)`; as with `before_start()` the `task_id` and `args` parameters can generally be ignored, while `retval` is the return value from `run()`, and `kwargs` will contain the user-specified variables passed into the Job execution.

#### The `on_failure()` Method

If either `before_start()` or `run()` raises any unhandled exception, the `on_failure()` method will be called next, if implemented. It has the signature `on_failure(self, exc, task_id, args, kwargs, einfo)`; of these parameters, the `exc` will contain the exception that was raised, and `kwargs` will contain the user-specified variables passed into the Job.

#### The `after_return()` Method

Regardless of the overall Job execution success or failure, the `after_return()` method will be called after `on_success()` or `on_failure()`. It has the signature `after_return(self, status, retval, task_id, args, kwargs, einfo)`; the `status` will indicate success or failure (using the `JobResultStatusChoices` enum), `retval` is *either* the return value from `run()` (on success) or the exception raised (on failure), and once again `kwargs` contains the user variables.

### Logging

+/- 2.0.0

Messages logged from a Job's logger will be stored in [`JobLogEntry`](../../user-guide/platform-functionality/jobs/models.md#job-log-entry) records associated with the current [`JobResult`](../../user-guide/platform-functionality/jobs/models.md#job-results).

The logger can be accessed either by using the `logger` property on the Job class or `nautobot.extras.jobs.get_task_logger(__name__)`. Both will return the same logger instance. For more information on the standard Python logging module, see the [Python documentation](https://docs.python.org/3/library/logging.html).

The logger accepts an `extra` kwarg that you can optionally set for the following features:

* `grouping`- Replaces the `active_test` Job property in Nautobot v1.X
* `object` - Replaces the `obj` kwarg in Nautobot v1.X Job logging methods
* `skip_db_logging` - Log the message to the console but not to the database

If a `grouping` is not provided it will default to the function name that logged the message. The `object` will default to `None`.

!!! example
    ```py
    from nautobot.apps.jobs import Job

    class MyJob(Job):
        def run(self):
            logger.info("This job is running!", extra={"grouping": "myjobisrunning", "object": self.job_result})
    ```

To skip writing a log entry to the database, set the `skip_db_logging` key in the "extra" kwarg to `True` when calling the log function. The output will still be written to the console.

!!! example
    ```py
    from nautobot.apps.jobs import Job

    class MyJob(Job):
        def run(self):
            logger.info("This job is running!", extra={"skip_db_logging": True})
    ```

Markdown rendering is supported for log messages, as well as [a limited subset of HTML](../../user-guide/platform-functionality/template-filters.md#render_markdown).

+/- 1.3.4 "Log entry sanitization"
    As a security measure, the `message` passed to any of these methods will be passed through the `nautobot.core.utils.logging.sanitize()` function in an attempt to strip out information such as usernames/passwords that should not be saved to the logs. This is of course best-effort only, and Job authors should take pains to ensure that such information is not passed to the logging APIs in the first place. The set of redaction rules used by the `sanitize()` function can be configured as [`settings.SANITIZER_PATTERNS`](../../user-guide/administration/configuration/settings.md#sanitizer_patterns).

+/- 2.0.0 "Significant API changes"
    The Job class logging functions (example: `self.log(message)`, `self.log_success(obj=None, message=message)`, etc) have been removed. Also, the convenience method to mark a Job as failed, `log_failure()`, has been removed. To replace the functionality of this method, you can log an error message with `self.logger.error()` and then raise an exception to fail the Job. Note that it is no longer possible to manually set the Job Result status as failed without raising an exception in the Job.

+/- 2.0.0
    The `AbortTransaction` class was moved from the `nautobot.utilities.exceptions` module to `nautobot.core.exceptions`. Jobs should generally import it from `nautobot.apps.exceptions` if needed.

+++ 2.4.0
    You can now use `self.logger.success()` to set the log level to `SUCCESS`.

### File Output

+++ 2.1.0

A Job can create files that will be saved and can later be downloaded by a user. (The specifics of how and where these files are stored will depend on your system's [`JOB_FILE_IO_STORAGE`](../../user-guide/administration/configuration/settings.md#job_file_io_storage) configuration.) To do so, use the `Job.create_file(filename, content)` method:

```python
from nautobot.extras.jobs import Job

class MyJob(Job):
    def run(self):
        self.create_file("greeting.txt", "Hello world!")
        self.create_file("farewell.txt", b"Goodbye for now!")  # content can be a str or bytes
```

The above Job when run will create two files, "greeting.txt" and "farewell.txt", that will be made available for download from the JobResult detail view's "Advanced" tab and via the REST API. These files will persist indefinitely, but can automatically be deleted if the JobResult itself is deleted; they can also be deleted manually by an administrator via the "File Proxies" link in the Admin UI.

The maximum size of any single created file (or in other words, the maximum number of bytes that can be passed to `self.create_file()`) is controlled by the [`JOB_CREATE_FILE_MAX_SIZE`](../../user-guide/administration/configuration/settings.md#job_create_file_max_size) system setting. A `ValueError` exception will be raised if `create_file()` is called with an overly large `content` value.

### Marking a Job as Failed

To mark a Job as failed, raise an exception from within the `run()` method. The exception message will be logged to the traceback of the Job Result. The Job Result status will be set to `failed`. To output a Job log message you can use the `self.logger.error()` method.

As an example, the following Job will fail if the user does not put the word "Taco" in `var1`:

```python
from nautobot.apps.jobs import Job, StringVar

class MyJob(Job):
    var1 = StringVar(...)

    def run(self, var1):
        if var1 != "Taco":
            self.logger.error("var1 must be 'Taco'")
            raise Exception("Argument input validation failed.")
```

### Accessing User and Job Result

+/- 2.0.0 "Significant API change"
    The `request` property has been changed to a Celery request instead of a Django web request and no longer includes the information from the web request that initiated the Job. The `user` object is now available as `self.user` instead of `self.request.user`.

The user that initiated the Job and the Job Result associated to the Job can be accessed through properties on the Job class:

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

While individual methods within your Job can and should be tested in isolation, you'll likely also want to test the entire execution of the Job.

+++ 1.3.3
    Entire Job execution testing was only introduced in 1.3.3 and newer.
    However the import paths used in the examples requires 1.5.2 and newer.

The simplest way to test the entire execution of Jobs is via calling the `nautobot.apps.testing.run_job_for_testing()` method, which is a helper wrapper around the `JobResult.enqueue_job` function used to execute a Job via Nautobot's Celery worker process.

Because of the way `run_job_for_testing` and more specifically Celery tasks work, which is somewhat complex behind the scenes, you need to inherit from `nautobot.apps.testing.TransactionTestCase` instead of `django.test.TestCase` (Refer to the [Django documentation](https://docs.djangoproject.com/en/stable/topics/testing/tools/#provided-test-case-classes) if you're interested in the differences between these classes - `TransactionTestCase` from Nautobot is a small wrapper around Django's `TransactionTestCase`).

When using `TransactionTestCase` (whether from Django or from Nautobot) each tests runs on a completely empty database. Furthermore, Nautobot requires new Jobs to be enabled before they can run. Therefore, we need to make sure the Job is enabled before each run which `run_job_for_testing` handles for us.

A simple example of a Job test case might look like the following:

```python
from nautobot.apps.testing import run_job_for_testing, TransactionTestCase
from nautobot.extras.models import Job, JobLogEntry


class MyJobTestCase(TransactionTestCase):
    def test_my_job(self):
        # Testing of Job "MyJob" in file "my_job_file.py" in $JOBS_ROOT
        job = Job.objects.get(job_class_name="MyJob", module_name="my_job_file")
        # or, job = Job.objects.get_for_class_path("local/my_job_file/MyJob")
        job_result = run_job_for_testing(job, var1="abc", var2=123)

        # Inspect the logs created by running the job
        log_entries = JobLogEntry.objects.filter(job_result=job_result)
        for log_entry in log_entries:
            self.assertEqual(log_entry.message, "...")
```

The test files should be placed under the `tests` folder in the app's directory or under JOBS_ROOT. The test can be run via `nautobot-server test [path to test in dotted directory format]` or `pytest [path to test in slash directory format]`.

!!! tip
    For running tests directly in the JOBS_ROOT, make sure the `JOBS_ROOT` environment variable is set.

!!! tip
    For more advanced examples refer to the Nautobot source code, specifically `nautobot/extras/tests/test_jobs.py`.

## Debugging Job Performance

+++ 1.5.17

Debugging the performance of Nautobot Jobs can be tricky, because they are executed in the worker context. In order to gain extra visibility, [cProfile](https://docs.python.org/3/library/profile.html) can be used to profile the Job execution.

The 'profile' form field on Jobs is automatically available when the `DEBUG` settings is `True`. When you select that checkbox, a profiling report in the pstats format will be written to the file system of the environment where the Job runs. Normally, this is on the file system of the worker process, but if you are using the `nautobot-server runjob` command with `--local`, it will end up in the file system of the web application itself. The path of the written file will be logged in the Job.

!!! note
    If you need to run this in an environment where `DEBUG` is `False`, you have the option of using `nautobot-server runjob` with the `--profile` flag. According to the docs, `cProfile` should have minimal impact on the performance of the Job; still, proceed with caution when using this in a production environment.

### Reading profiling reports

A full description on how to deal with the output of `cProfile` can be found in the [Instant User's Manual](https://docs.python.org/3/library/profile.html#instant-user-s-manual), but here is something to get you started:

```python
import pstats
job_result_uuid = "66b70231-002f-412b-8cc4-1cc9609c2c9b"
stats = pstats.Stats(f"/tmp/nautobot-jobresult-{job_result_uuid}.pstats")
stats.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(10)
```

This will print the 10 functions that the Job execution spent the most time in - adapt this to your needs!

## Example Jobs

### Example "Everything" Job

The "Example App" included with the Nautobot source code [includes a number of simple sample Jobs](https://github.com/nautobot/nautobot/blob/main/examples/example_app/example_app/jobs.py), including an `ExampleEverythingJob` class that demonstrates and documents the usage of the various metadata attributes, input variable types, and magic methods that a Job can support. As Job functionality will continue to evolve over time, if using this file as a reference, please make sure that you're viewing the version of this Job that corresponds to your target Nautobot version.

### Creating objects for a planned location

This Job prompts the user for three variables:

* The name of the new location
* The device model (a filtered list of defined device types)
* The number of access switches to create

These variables are presented as a web form to be completed by the user. Once submitted, the Job's `run()` method is called to create the appropriate objects, and it returns simple CSV output to the user summarizing the created objects.

```python
from django.contrib.contenttypes.models import ContentType

from nautobot.apps.jobs import Job, StringVar, IntegerVar, ObjectVar, register_jobs
from nautobot.dcim.models import Location, LocationType, Device, Manufacturer, DeviceType
from nautobot.extras.models import Status, Role

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

    def run(self, *, location_name, switch_count, switch_model, manufacturer=None):
        STATUS_PLANNED = Status.objects.get(name="Planned")

        # Create the new location
        root_type, lt_created = LocationType.objects.get_or_create(name="Campus")
        device_ct = ContentType.objects.get_for_model(Device)
        root_type.content_types.add(device_ct)
        location = Location(
            name=location_name,
            location_type=root_type,
            status=STATUS_PLANNED,
        )
        location.validated_save()
        self.logger.info("Created new location", extra={"object": location})

        # Create access switches
        switch_role, r_created = Role.objects.get_or_create(name="Access Switch")
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

register_jobs(NewBranch)
```

### Device validation

A Job to perform various validation of Device data in Nautobot. As this Job does not require any user input, it does not define any variables.

```python
from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import ConsolePort, Device, PowerPort
from nautobot.extras.models import Status


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
            if connected_ports < 2:
                self.logger.error(
                    "%s connected power supplies found (2 needed)",
                    connected_ports,
                    extra={"object": device},
                )
            else:
                self.logger.info("At least two connected power supplies found", extra={"object": device})

    def run(self):
        self.test_console_connection()
        self.test_power_connections()


register_jobs(DeviceConnectionsReport)
```

## Job Button Receivers

Job Buttons are only able to initiate a specific type of Job called a **Job Button Receiver**. These are Jobs that subclass the `nautobot.apps.jobs.JobButtonReceiver` class. Job Button Receivers are similar to normal Jobs except they are hard coded to accept only `object_pk` and `object_model_name` [variables](#variables). The `JobButtonReceiver` class only implements one method called `receive_job_button`.

!!! note "Disabled by default just like other Jobs"
    Job Button Receivers still need to be [enabled through the web UI](../../user-guide/platform-functionality/jobs/index.md#enabling-jobs-for-running) before they can be used just like other Jobs.

### The `receive_job_button()` Method

All `JobButtonReceiver` subclasses must implement a `receive_job_button()` method. This method accepts only one argument:

1. `obj` - An instance of the object where the button was pressed

### Example Job Button Receiver

```py
from nautobot.apps.jobs import JobButtonReceiver, register_jobs


class ExampleSimpleJobButtonReceiver(JobButtonReceiver):
    class Meta:
        name = "Example Simple Job Button Receiver"

    def receive_job_button(self, obj):
        self.logger.info("Running Job Button Receiver.", extra={"object": obj})
        # Add job logic here


register_jobs(ExampleSimpleJobButtonReceiver)
```

### Job Buttons for Multiple Types

Since Job Buttons can be associated to multiple object types, it would be trivial to create a Job that can change what it runs based on the object type.

```py
from nautobot.apps.jobs import JobButtonReceiver, register_jobs
from nautobot.dcim.models import Device, Location


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


register_jobs(ExampleComplexJobButtonReceiver)
```

## Job Hook Receivers

Job Hooks are only able to initiate a specific type of Job called a **Job Hook Receiver**. These are Jobs that subclass the `nautobot.apps.jobs.JobHookReceiver` class. Job Hook Receivers are similar to normal Jobs except they are hard coded to accept only an `object_change` [variable](#variables). The `JobHookReceiver` class only implements one method called `receive_job_hook`.

!!! warning "No support for `approval_required` at this time"
    Requiring approval for execution of Job Hooks by setting the `Meta.approval_required` attribute to `True` on your `JobHookReceiver` subclass is not supported. The value of this attribute will be ignored. Support for requiring approval of Job Hooks will be added in a future release.

!!! important "No recursive JobHookReceivers"
    To prevent negatively impacting system performance through an infinite loop, a change that was made by a `JobHookReceiver` Job will not trigger another `JobHookReceiver` Job to run.

### Example Job Hook Receiver

```py
from nautobot.apps.jobs import JobHookReceiver, register_jobs
from nautobot.extras.choices import ObjectChangeActionChoices


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


register_jobs(ExampleJobHookReceiver)
```

### The `receive_job_hook()` Method

All `JobHookReceiver` subclasses must implement a `receive_job_hook()` method. This method accepts three arguments:

1. `change` - An instance of `nautobot.extras.models.ObjectChange`
2. `action` - A string with the action performed on the changed object ("create", "update" or "delete")
3. `changed_object` - An instance of the object that was changed, or `None` if the object has been deleted
