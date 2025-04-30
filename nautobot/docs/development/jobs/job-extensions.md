# Job Extensions

In addition to standard Jobs, Nautobot supports two specialized types of Jobs that respond to specific events:

- **Job Button Receivers**: Triggered by a button click on a specific object (e.g., a Device or Location)
- **Job Hook Receivers**: Automatically triggered in response to object changes (create, update, delete)

These extensions let you tightly couple automation to user actions or system changes without requiring manual Job execution from the Jobs view.

## Job Button Receivers

These are Jobs that subclass the `nautobot.apps.jobs.JobButtonReceiver` class. Job Button Receivers are similar to normal Jobs except they are hard coded to accept only `object_pk` and `object_model_name` [variables](./job-structure.md#variables). The `JobButtonReceiver` class only implements one method called `receive_job_button`.

!!! note "Disabled by default just like other Jobs"
    Job Button Receivers still need to be [enabled through the web UI](../../user-guide/platform-functionality/jobs/managing-jobs.md#enabling-and-disabling-jobs) before they can be used just like other Jobs.

### The `receive_job_button()` Method

All `JobButtonReceiver` subclasses must implement `receive_job_button(self, obj)`, where `obj` is the instance of the model where the button was pressed.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example "Example Job Button Receiver"
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

Since Job Buttons can be associated to multiple object types, it would be easy to create a Job that can change what it runs based on the object type.

You can support multiple object types in a single Job by checking the object type using `isinstance()` and performing permission checks with `self.user.has_perm()`.

!!! tip "Checking Permissions"
    You can use `self.user.has_perm()` to restrict logic based on the object or user's role.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
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

A Job Hook Receiver listens for database changes and runs automatically when an object is created, updated, or deleted. Job Hooks are only able to initiate a specific type of Job called a **Job Hook Receiver**. These are Jobs that subclass the `nautobot.apps.jobs.JobHookReceiver` class. Job Hook Receivers are similar to normal Jobs except they are hard coded to accept only an `object_change` [variable](./job-structure.md#variables). The `JobHookReceiver` class only implements one method called `receive_job_hook`.

Use Job Hooks to enforce policy, run audits, or trigger external actions in response to changes.

!!! warning "No support for `approval_required` at this time"
    Requiring approval for execution of Job Hooks by setting the `Meta.approval_required` attribute to `True` on your `JobHookReceiver` subclass is not supported. The value of this attribute will be ignored. Support for requiring approval of Job Hooks may be added in a future release.

!!! important "No recursive JobHookReceivers"
    To prevent negatively impacting system performance through an infinite loop, a change that was made by a `JobHookReceiver` Job will not trigger another `JobHookReceiver` Job to run.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example "Example Job Hook Receiver"
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

All `JobHookReceiver` subclasses must implement `receive_job_hook(self, change, action, changed_object)`, which receives:

1. `change`: the `ObjectChange` instance that triggered the hook
2. `action`: A string with the action performed on the changed object - one of `"create"`, `"update"`, or `"delete"`
3. `changed_object`: An instance of the object that was changed, or `None` if the object has been deleted

In the example above, the Job inspects changes to the `serial` field and reverts them if they don't meet custom criteria. It also logs differences using `change.get_snapshots()` and avoids acting on delete events. This kind of hook is useful for enforcing policy or catching problematic edits before they propagate further.

If the action is `"delete"`, the method exits early since `changed_object` is `None`.

!!! note
    You can use the `change` object to inspect more detailed diffs if needed. See the [`ObjectChange`](../../user-guide/platform-functionality/change-logging.md#objectchange) docs for more.
