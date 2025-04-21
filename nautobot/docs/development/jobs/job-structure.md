
### Module Metadata Attributes
<!-- move:job-structure.md -->
#### `name` (Grouping)
<!-- move:job-structure.md -->
You can define a global constant called `name` within a job module (the Python file which contains one or more Job classes) to set the default grouping under which the Jobs in this module will be displayed in the Nautobot UI. If this value is not defined, the module's file name will be used. This "grouping" value may also be defined or overridden when editing Job records in the database.

!!! note
    In some UI elements and API endpoints, the module file name is displayed in addition to or in place of this attribute, so even if defining this attribute, you should still choose an appropriately explanatory file name as well.

### Class Metadata Attributes
<!-- move:job-structure.md -->
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

+/- 2.0.0 "No automatic functionality"
    The `read_only` flag no longer changes the behavior of Nautobot core and is up to the Job author to decide whether their Job should be considered read only.

Default: `False`

A boolean that can be set by the Job author to indicate that the Job does not make any changes to the environment. What behavior makes each Job "read only" is up to the individual Job author to decide. Note that user input may still be optionally collected with read-only Jobs via Job variables, as described below.

#### `soft_time_limit`

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

Default: `[]`

A list of Job Queue names that the Job can be routed to. An empty list will default to only allowing the user to select the [default Celery queue](../../user-guide/administration/configuration/settings.md#celery_task_default_queue) (`default` unless changed by an administrator). The queue specified in the Job's `default_job_queue` will be used if a queue is not specified in a Job run API call.

+/- 2.4.0 "Changed default queue selection"
    As a result of the addition of Job Queues, the default queue when running a Job without explicitly selecting a queue is now the job queue specified in the `default_job_queue` field on the Job model. `default_job_queue` fields for any existing Job instances are automatically populated with the name of the first entry in `task_queues` list of the Job class. When `task_queues` list on the Job class is empty, the corresponding Job instance's `default_job_queue` will be the job queue with the name provided by `settings.CELERY_TASK_DEFAULT_QUEUE`. You can also override the initial `default_job_queue` by setting `default_job_queue_override` to True and assign the field with a different Job Queue instance.

!!! note
    A worker must be listening on the requested queue or the Job will not run. See the documentation on [task queues](../../user-guide/administration/guides/celery-queues.md) for more information.

#### `template_name`

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
<!-- move:job-structure.md -->
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
<!-- move:job-structure.md -->
Nautobot Jobs when executed will be instantiated by Nautobot, then Nautobot will call in order the special API methods `before_start()`, `run()`, `on_success()`/`on_failure()`, and `after_return()`. You must implement the `run()` method; the other methods have default implementations that do nothing.

As Jobs are Python classes, you are of course free to define any number of other helper methods or functions that you call yourself from within any of the above special methods, but the above are the only ones that will be automatically called.

--- 2.0.0 "Removal of `test` and `post_run` special methods"
    The NetBox backwards compatible `test_*()` and `post_run()` special methods have been removed.

#### The `before_start()` Method

The `before_start()` method may optionally be implemented to perform any appropriate Job-specific setup before the `run()` method is called. It has the signature `before_start(self, task_id, args, kwargs)` for historical reasons; the `task_id` parameter will always be identical to `self.request.id`, the `args` parameter will generally be empty, and any user-specified variables passed into the Job execution will be present in the `kwargs` parameter.

The return value from `before_start()` is ignored, but if it raises any exception, the Job result status will be marked as `FAILURE` and `run()` will not be called.

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

If `run()` returns any value (even the implicit `None`), the returned value will be stored in the associated JobResult database record. (The Job Result will be marked as `SUCCESS` unless the `fail()` method was called at some point during `run()`, in which case it will be marked as `FAILURE`.) Conversely, if `run()` raises any exception, the Job execution will be marked as `FAILURE` and the traceback will be stored in the JobResult.

#### The `on_success()` Method

If both `before_start()` and `run()` are successful, the `on_success()` method will be called next, if implemented. It has the signature `on_success(self, retval, task_id, args, kwargs)`; as with `before_start()` the `task_id` and `args` parameters can generally be ignored, while `retval` is the return value from `run()`, and `kwargs` will contain the user-specified variables passed into the Job execution.

#### The `on_failure()` Method

If either `before_start()` or `run()` raises any unhandled exception, or reports a failure overall through `fail()`, the `on_failure()` method will be called next, if implemented. It has the signature `on_failure(self, exc, task_id, args, kwargs, einfo)`; of these parameters, the `exc` will contain the exception that was raised (if any) or the return value from `before_start()` or `run()` (otherwise), and `kwargs` will contain the user-specified variables passed into the Job.

#### The `after_return()` Method

Regardless of the overall Job execution success or failure, the `after_return()` method will be called after `on_success()` or `on_failure()`. It has the signature `after_return(self, status, retval, task_id, args, kwargs, einfo)`; the `status` will indicate success or failure (using the `JobResultStatusChoices` enum), `retval` is *either* the return value from `run()` or the exception raised, and once again `kwargs` contains the user variables.
