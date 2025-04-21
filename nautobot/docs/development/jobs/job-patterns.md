
### Logging
<!-- move:job-patterns.md -->
+/- 2.0.0

Messages logged from a Job's logger will be stored in [`JobLogEntry`](../../user-guide/platform-functionality/jobs/models.md#job-log-entry) records associated with the current [`JobResult`](../../user-guide/platform-functionality/jobs/models.md#job-results).

The logger can be accessed either by using the `logger` property on the Job class or `nautobot.extras.jobs.get_task_logger(__name__)`. Both will return the same logger instance. For more information on the standard Python logging module, see the [Python documentation](https://docs.python.org/3/library/logging.html).

The logger accepts an `extra` kwarg that you can optionally set for the following features:

* `grouping`- Replaces the `active_test` Job property in Nautobot v1.X
* `object` - Replaces the `obj` kwarg in Nautobot v1.X Job logging methods
* `skip_db_logging` - Log the message to the console but not to the database

If a `grouping` is not provided it will default to the function name that logged the message. The `object` will default to `None`.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    from nautobot.apps.jobs import Job

    class MyJob(Job):
        def run(self):
            self.logger.info("This job is running!", extra={"grouping": "myjobisrunning", "object": self.job_result})
    ```

To skip writing a log entry to the database, set the `skip_db_logging` key in the "extra" kwarg to `True` when calling the log function. The output will still be written to the console.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    from nautobot.apps.jobs import Job

    class MyJob(Job):
        def run(self):
            self.logger.info("This job is running!", extra={"skip_db_logging": True})
    ```

Markdown rendering is supported for log messages, as well as [a limited subset of HTML](../../user-guide/platform-functionality/template-filters.md#render_markdown).

!!! warning
    As a security measure, the `message` passed to any of these methods will be passed through the `nautobot.core.utils.logging.sanitize()` function in an attempt to strip out information such as usernames/passwords that should not be saved to the logs. This is of course best-effort only, and Job authors should take pains to ensure that such information is not passed to the logging APIs in the first place. The set of redaction rules used by the `sanitize()` function can be configured as [`settings.SANITIZER_PATTERNS`](../../user-guide/administration/configuration/settings.md#sanitizer_patterns).

+/- 2.0.0 "Significant API changes"
    The Job class logging functions (example: `self.log(message)`, `self.log_success(obj=None, message=message)`, etc) have been removed. Also, the convenience method to mark a Job as failed, `log_failure()`, has been removed. To replace the functionality of this method, you can log an error message with `self.logger.error()` and then raise an exception to fail the Job. Note that it is no longer possible to manually set the Job Result status as failed without raising an exception in the Job.

+/- 2.0.0
    The `AbortTransaction` class was moved from the `nautobot.utilities.exceptions` module to `nautobot.core.exceptions`. Jobs should generally import it from `nautobot.apps.exceptions` if needed.

+++ 2.4.0 "`logger.success()` added"
    You can now use `self.logger.success()` to log a message at the level `SUCCESS`, which is located between the standard `INFO` and `WARNING` log levels.

+++ 2.4.5 "`logger.failure()` added"
    You can now use `self.logger.failure()` to log a message at the level `FAILURE`, which is located between the standard `WARNING` and `ERROR` log levels.

### File Output
<!-- move:job-patterns.md -->
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
<!-- move:job-patterns.md -->
Any uncaught exception raised from within the `run()` method will abort the `run()` method immediately (as usual in Python), and will result in the Job Result status being marked as `FAILURE`. The exception message and traceback will be recorded in the Job Result.

Alternatively, in Nautobot v2.4.5 and later, you can more "cleanly" fail a Job by calling `self.fail(...)` and then either returning immediately from the `run()` method or continuing with the execution of the Job, as desired. In this case, after the `run()` method completes, the Job Result status will be automatically marked as `FAILURE` and no exception or traceback will be recorded.

As an example, the following Job will abort if the user does not put the word "Taco" in `occasion`, and fail (but not abort) if the variable does not additionally contain "Tuesday":

```python
from nautobot.apps.jobs import Job, StringVar

class MyJob(Job):
    occasion = StringVar(...)

    def run(self, occasion):
        if not occasion.startswith("Taco"):
            self.logger.failure("The occasion must begin with 'Taco'")
            raise Exception("Argument input validation failed.")
        if not occasion.endswith(" Tuesday"):
            self.fail("It's supposed to be Tuesday")
        self.logger.info("Today is %s", occasion)
        return occasion
```

### Accessing User and Job Result
<!-- move:job-patterns.md -->
+/- 2.0.0 "Significant API change"
    The `request` property has been changed to a Celery request instead of a Django web request and no longer includes the information from the web request that initiated the Job. The `user` object is now available as `self.user` instead of `self.request.user`.

The user that initiated the Job and the Job Result associated to the Job can be accessed through properties on the Job class:

```py
username = self.user.username
job_result_id = self.job_result.id
self.logger.info("Job %s initiated by user %s is running.", job_result_id, username)
```

### Reading Data from Files
<!-- move:job-patterns.md -->
The `Job` class provides two convenience methods for reading data from files:

* `load_yaml`
* `load_json`

These two methods will load data in YAML or JSON format, respectively, from files within the local path (i.e. `JOBS_ROOT/`).



## Example Jobs
<!-- move:job-patterns.md -->
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