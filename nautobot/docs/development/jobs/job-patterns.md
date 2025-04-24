# Job Patterns

Jobs in Nautobot are extremely flexible—they can take user input, query the database, talk to devices, generate reports, and more. But because they’re built in Python, there’s no “one right way” to do any of those tasks.

This page provides a catalog of **common patterns** used when building Jobs, especially those that go beyond the basics of the `run()` method. These examples are designed to be **practical, modular, and reusable**—you can pick and choose the parts that make sense for your own Job logic.

Because Jobs are highly flexible, many common patterns tend to emerge depending on what the Job is trying to accomplish — like importing data, validating configuration, logging results, or returning output to users.  

Not every Job needs every feature shown below. Use this page as a reference: copy/paste and customize only the patterns you need.


## Common Job Patterns

- [Preparing and Structuring Jobs](#job-setup-and-context-access)
    - Accessing user and Job metadata
    - Using helper methods and structuring multi-step Jobs
- [Logging Patterns](#logging-patterns)
    - Writing structured log messages
    - Skipping database logging
    - Logging Markdown or HTML safely
- [Job Flow Control](#job-flow-control)
    - Marking a Job as failed (`self.fail()`)
    - Failing via exceptions
  - Guard clauses and validation
- [Working with Files](#working-with-files)
    - Uploading and parsing files (`FileVar`)
    - Creating downloadable files (`create_file()`)
    - Reading static YAML/JSON files (`load_yaml` / `load_json`)
- [Structured Output](#structured-output)
    - Returning structured results like CSV or JSON
    - Rendering result tables in the UI
- [Scheduled or Approved Jobs](#scheduled-or-approved-jobs)
    - Writing Jobs that support future execution
    - Avoiding `has_sensitive_variables` for compatibility
- [Reference Implementations](#reference-implementations)
    - Full examples from Nautobot and community sources

## Job Execution Context and Logging Patterns

When writing Jobs, it's helpful to access information about the current execution—like which user ran the Job or which JobResult is being updated. It’s equally important to log progress or results in a way that’s visible in both the Nautobot UI and REST API.

This section covers how to use the built-in logger, including structured log messages, context-aware logging, and optional enhancements like skipping database logging or using Markdown formatting.

### Accessing User and Job Context

The user who initiated the Job and the associated `JobResult` are available via the `self.user` and `self.job_result` properties of the Job class.

This information is useful for:

- **Personalization** — customizing behavior or output based on the user
- **Auditing** — logging who ran what, and when
- **Conditional logic** — restricting actions to admins or specific users
- **Debugging** — correlating job logs with user sessions or API activity

Here’s a simple example that logs which user launched the Job, along with its unique result ID:

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    username = self.user.username
    job_result_id = self.job_result.id
    self.logger.info("Job %s initiated by user %s is running.", job_result_id, username)
    ```

You can access other standard Django user attributes like `self.user.email`, `self.user.is_staff`, or use `self.user.has_perm(...)` for permission checks.

### Logging Patterns
+/- 2.0.0

Nautobot logs messages from Jobs in a structured way, storing them as part of the `JobResult` and displaying them in the UI. This enables Jobs to provide real-time feedback, track their progress, and surface success or failure messages clearly to the user.

Use the `self.logger` property to write log messages from within your Job code. These logs appear in the UI and are also saved as [`JobLogEntry`](../../user-guide/platform-functionality/jobs/models.md#job-log-entry) records associated with the current [`JobResult`](../../user-guide/platform-functionality/jobs/models.md#job-results).

#### Logging Levels

Nautobot supports standard logging levels, with additional custom levels for success and failure messages:

| Level   | Method                 | Description                               |
|---------|------------------------|-------------------------------------------|
| DEBUG   | `self.logger.debug()`  | Detailed diagnostic information.          |
| INFO    | `self.logger.info()`   | General operational messages.             |
| SUCCESS | `self.logger.success()`| Indicates successful operations.          |
| WARNING | `self.logger.warning()`| Signals potential issues.                 |
| FAILURE | `self.logger.failure()`| Denotes failed operations.                |
| ERROR   | `self.logger.error()`  | Serious errors that prevent execution.    |
| CRITICAL| `self.logger.critical()`| Critical conditions.                      |

!!! note
    `logger.success()` and `logger.failure()` were introduced in versions 2.4.0 and 2.4.5, respectively.

#### Writing Log Messages

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    self.logger.info("Job is starting.")
    self.logger.error("An unexpected error occurred.")
    self.logger.success("Provisioning complete.")
    ```

For most use cases, you'll use `self.logger`. You can also obtain the same logger via `nautobot.extras.jobs.get_task_logger(__name__)`, though this is less common.

#### Structured Log Context with `extra`

You can attach structured metadata to log messages using the `extra` parameter. This enables grouping and improves how logs are displayed or queried:

- `grouping`: A logical group name for related messages, shown in the UI as expandable sections
- `object`: A Nautobot object instance to associate with this log message (e.g., a Device)
- `skip_db_logging`: Set to `True` to avoid saving the log message in the database

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    self.logger.info(
        "Validated device",
        extra={
            "grouping": "inventory-check",
            "object": device
        }
    )
    ```

To skip writing a log entry to the database but still print it to the console:

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    self.logger.info("Debugging message", extra={"skip_db_logging": True})
    ```

If `grouping` is not specified, Nautobot uses the current function name as a default. If `object` is omitted, the log is not associated with any model instance.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    from nautobot.apps.jobs import Job

    class MyJob(Job):
        def run(self):
            self.logger.info("This job is running!", extra={"grouping": "myjobisrunning", "object": self.job_result})
    ```

#### Log Message Formatting

Log messages can include Markdown formatting, and [a limited subset of HTML](../../user-guide/platform-functionality/template-filters.md#render_markdown) is also supported for added emphasis in the UI.

#### Sanitizing Log Messages

As a security precaution, Nautobot passes all log messages through `nautobot.core.utils.logging.sanitize()` to remove sensitive information like passwords or tokens. You should still avoid logging such values yourself, as this redaction is best-effort. The sanitization behavior can be customized using [`settings.SANITIZER_PATTERNS`](../../user-guide/administration/configuration/settings.md#sanitizer_patterns).

+/- 2.0.0 "Significant API changes"
    The Job class logging functions (example: `self.log(message)`, `self.log_success(obj=None, message=message)`, etc) have been removed. Also, the convenience method to mark a Job as failed, `log_failure()`, has been removed. To replace the functionality of this method, you can log an error message with `self.logger.error()` and then raise an exception to fail the Job. Note that it is no longer possible to manually set the Job Result status as failed without raising an exception in the Job.

+/- 2.0.0
    The `AbortTransaction` class was moved from the `nautobot.utilities.exceptions` module to `nautobot.core.exceptions`. Jobs should generally import it from `nautobot.apps.exceptions` if needed.

+++ 2.4.0 "`logger.success()` added"
    You can now use `self.logger.success()` to log a message at the level `SUCCESS`, which is located between the standard `INFO` and `WARNING` log levels.

+++ 2.4.5 "`logger.failure()` added"
    You can now use `self.logger.failure()` to log a message at the level `FAILURE`, which is located between the standard `WARNING` and `ERROR` log levels.

## Job Flow Control

Nautobot Jobs can exit in a variety of ways—cleanly, with validation errors, or due to unexpected exceptions. This section covers techniques for controlling Job execution and determining how success or failure is reported.

These patterns help you:

- Exit early if required conditions aren’t met (“guard clauses”)
- Fail with or without tracebacks
- Understand how Job completion status is determined and reported

### Guard Clauses with Validation

Use guard clauses to validate inputs and exit early when conditions aren’t met. This pattern keeps Job logic clean and prevents unnecessary processing.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    if not user_input:
        self.fail("User input was missing.")
        return
    ```

### Success and Failure Conditions

A Job’s result is determined by how the `run()` method completes:

- If `run()` completes without raising an exception and does **not** call `self.fail()`, the Job is marked **`SUCCESS`**.
- If `run()` **raises an exception**, the Job is marked **`FAILURE`** and the exception traceback is stored in the `JobResult`.
- If you call `self.fail("message")`, the Job **completes normally**, but is still marked **`FAILURE`** (no traceback is recorded).
- If `run()` returns a value, that value is saved to the `JobResult` and displayed in the UI and API.

!!! tip
    For more, see [The `run()` Method](../job-structure.md#the-run-method) in the Job Structure guide.

This pattern lets you validate inputs, selectively fail under certain conditions, and return structured summaries or results.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example "Mixed Flow Handling"
    ```py
    from nautobot.apps.jobs import Job, StringVar, IntegerVar, register_jobs

    class LunchOrder(Job):
        name = StringVar(description="What are you ordering?")
        quantity = IntegerVar(description="How many?", default=1)

        def run(self, *, name, quantity):
            if not name:
                self.fail("No order provided.")
                return

            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")

            self.logger.info("Order received: %d x %s", quantity, name)
            return f"Order summary: {quantity} x {name}"

    register_jobs(LunchOrder)
    ```

- If `name` is empty, the Job completes but is marked as `FAILURE` (via `self.fail()`).
- If `quantity` is invalid, it raises an exception and aborts immediately.
- If both values are valid, the Job logs the order and returns a string that’s shown in the `JobResult`.

This approach demonstrates how you can gracefully handle invalid inputs with `self.fail()` while still using exceptions to halt execution for more serious issues—giving you precise control over how and why a Job is marked as failed.

### Marking a Job as Failed

Nautobot Jobs can exit in a variety of ways—cleanly, with validation checks, or due to exceptions. This section shows how to control Job execution and how success or failure gets reported to users.

Any uncaught exception raised from within the `run()` method will abort the `run()` method immediately (as usual in Python), and will result in the Job Result status being marked as `FAILURE`. The exception message and traceback will be recorded in the Job Result.

Alternatively, in Nautobot v2.4.5 and later, you can more "cleanly" fail a Job by calling `self.fail(...)` and then either returning immediately from the `run()` method or continuing with the execution of the Job, as desired. In this case, after the `run()` method completes, the Job Result status will be automatically marked as `FAILURE` and no exception or traceback will be recorded.

As an example, the following Job will abort if the user does not put the word "Taco" in `occasion`, and fail (but not abort) if the variable does not additionally contain "Tuesday":

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
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

## Working with Files

Jobs can accept uploaded files, return output files, and read static data from disk. This section outlines how to use each of these patterns effectively.

- **Output Files** — Use `create_file()` to generate downloadable content
- **Input Files** — Use `FileVar` to let users upload temporary files
- **Static Files** — Use `load_yaml()` or `load_json()` to read bundled config files

For a detailed explanation and example of how to use `FileVar` to accept uploaded files from users, see [FileVar in Job Structure](./job-structure.md#filevar).

### File Output

+++ 2.1.0

Jobs can generate output files that will be saved and made available to the user after execution. These files are exposed in the JobResult detail view (under the **Advanced** tab) and via the REST API.

Use the `Job.create_file(filename, content)` method:

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    from nautobot.extras.jobs import Job

    class MyJob(Job):
        def run(self):
            self.create_file("greeting.txt", "Hello world!")
            self.create_file("farewell.txt", b"Goodbye for now!")  # Content can be a str or bytes
    ```

The files will persist alongside the JobResult unless explicitly deleted. They can also be removed via the Admin UI under **File Proxies**.

!!! note
    The maximum allowed size for any single file is controlled by the [`JOB_CREATE_FILE_MAX_SIZE`](../../user-guide/administration/configuration/settings.md#job_create_file_max_size) setting. If this limit is exceeded, `create_file()` will raise a `ValueError`.

Output files created via `create_file()` are persistent and linked to the JobResult for future download. In contrast, input files received through variables like `FileVar` exist in memory only during Job execution and are not saved unless your Job explicitly does so.

### Uploading and Parsing Files

To accept user-provided files at runtime, use [`FileVar`](./job-structure.md#filevar). These files are passed into the Job’s `run()` method as in-memory objects and must be read and processed during execution. They are not saved automatically.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    import csv
    from nautobot.apps.jobs import Job, FileVar, register_jobs

    class ProcessCSV(Job):
        class Meta:
            name = "Process CSV File"

        input_file = FileVar(description="Upload a CSV file with 'hostname' and 'ip_address' columns")

        def run(self, *, input_file):
            decoded_file = input_file.read().decode("utf-8").splitlines()
            reader = csv.DictReader(decoded_file)
            for row in reader:
                self.logger.info("Device: %s | IP: %s", row["hostname"], row["ip_address"])

    register_jobs(ProcessCSV)
    ```

This pattern is useful when building import workflows or onboarding pipelines that take structured data from users. If you want to retain the uploaded file or transform it into an output, use `create_file()`.

!!! note
    Files provided through `FileVar` are temporary and exist only in memory during execution. They must be read and processed within the `run()` method.

### Reading Static Data from Files

Jobs can also load local static files that are shipped alongside the Job source. These are useful for reading predefined content like templates, inventory definitions, or configuration settings.

Use the following convenience methods to load structured data:

- `load_yaml("filename.yaml")`
- `load_json("filename.json")`

These paths are relative to the Job’s file location inside `$JOBS_ROOT/`.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    from nautobot.apps.jobs import Job

    class LoadConfig(Job):
        def run(self):
            config = self.load_yaml("defaults.yaml")
            self.logger.info("Loaded configuration with %d items.", len(config))
    ```

Unlike uploaded files, static files are typically bundled with the Job and version-controlled. This makes them useful for Jobs that rely on standard schemas or reusable templates.

## Reference Implementations

The examples below demonstrate fully working Jobs from the Nautobot ecosystem. They're meant to serve as inspiration and guidance when building your own Jobs—especially if you're not sure where to start or want to see how others have structured their code.

Some Jobs are simple and focused (like validating devices), while others combine multiple input types and outputs. Use these as starting points, or to understand common patterns in action.

### Device Validation

This Job performs checks to ensure all active devices in Nautobot meet certain physical connection criteria. It does not require any user input.

This Job is useful when enforcing operational standards in environments where minimum connectivity (e.g., console and dual power) is expected. It demonstrates how to iterate over Nautobot models, access related objects, and use structured logging with `extra`. Since it defines no variables, it can be run immediately by any user with Job permissions.

!!! note "Requirements"
    - Devices must exist in the database with `status="Active"`
    - ConsolePort and PowerPort relationships should be populated
    - The `Status` model must include an `"Active"` value

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
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

### Creating objects for a planned location

This Job illustrates multiple patterns in combination: conditional form rendering (`query_params`), dynamic object creation with model relationships, and structured output formatting. It’s a strong reference for provisioning-style workflows or batch creation Jobs. To run it successfully, the system should already have appropriate Device Types and Statuses defined (e.g., “Planned”), and the user must have permission to create DCIM objects like `Device` and `Location`.

This Job prompts the user for three variables:

- The name of the new location  
- The device model (a filtered list of defined device types)  
- The number of access switches to create  

These variables are presented as a web form to be completed by the user. Once submitted, the Job's `run()` method is called to create the appropriate objects, and it returns simple CSV output to the user summarizing the created objects.

!!! note "Requirements"
    - The `"Planned"` Status must exist in the Status model  
    - The `"Access Switch"` Role must either exist or will be created  
    - DeviceType and Manufacturer records must exist and be related  
    - The user must have permission to create `Location` and `Device` objects

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
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


### Example "Everything" Job

The [Example App](https://github.com/nautobot/nautobot/blob/main/examples/example_app/example_app/jobs.py) included with Nautobot provides several sample Jobs, including an `ExampleEverythingJob` class. This Job is designed to showcase a wide range of capabilities that a Job class can support—making it a useful reference for exploring what’s possible when combining inputs, lifecycle hooks, and outputs in one place.

The snippet below demonstrates a mix of common patterns: variable types (`StringVar`, `ChoiceVar`, `FileVar`), structured logging, lifecycle methods like `before_start()` and `on_success()`, and file output using `create_file()`. It's a helpful starting point when you want to build a full-featured Job that accepts input, produces artifacts, and reports structured progress through the UI.

!!! note
    This snippet highlights only a portion of the full `ExampleEverythingJob`. To explore the complete implementation—including additional variables, error handling with `on_failure()`, and form customization—see the [full source code in the Example App](https://github.com/nautobot/nautobot/blob/main/examples/example_app/example_app/jobs.py).

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    from nautobot.apps.jobs import Job, StringVar, IntegerVar, BooleanVar, ChoiceVar, FileVar, register_jobs

    class ExampleEverythingJob(Job):
        class Meta:
            name = "Everything Demo"
            description = "Demonstrates many Job features"
            field_order = ["example_string", "example_choice"]

        example_string = StringVar(description="A text input.")
        example_choice = ChoiceVar(
            choices=[("a", "Alpha"), ("b", "Beta")],
            description="Pick a choice."
        )
        example_file = FileVar(description="Upload a file.")

        def before_start(self, task_id, args, kwargs):
            self.logger.info("Before starting job.")

        def run(self, *, example_string, example_choice, example_file):
            self.logger.info("Received string: %s", example_string)
            self.logger.info("Choice selected: %s", example_choice)
            file_content = example_file.read().decode("utf-8")
            self.create_file("copy.txt", file_content)
            return "Done!"

        def on_success(self, retval, task_id, args, kwargs):
            self.logger.success("Job completed successfully.")
    ```
