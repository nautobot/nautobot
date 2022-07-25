# Job Hooks

A Job Hook is a mechanism for automatically starting a [job](./jobs.md) when an object is changed. Job Hooks are similar to [webhooks](../models/extras/webhook.md) except that an object change event initiates a `JobHookReceiver` job instead of a web request. Job hooks are configured in the web UI under **Jobs > Job Hooks**.

## Job Hook Receivers

Job Hooks are only able to initiate a specific type of job called a **Job Hook Receiver**. These are jobs that subclass the `nautobot.extras.jobs.JobHookReceiver` class. Job hook receivers are similar to normal jobs except they are hard coded to accept only an `object_change` [variable](jobs.md#variables). Job Hook Receivers are hidden from the jobs listing UI by default but otherwise function similarly to other jobs. The `JobHookReceiver` class only implements one method called `receive_job_hook`.

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
        self.log_info(f"DIFF: {snapshots['differences']}")

        # validate changes to serial field
        if "serial" in snapshots["differences"]["added"]:
            old_serial = snapshots["differences"]["removed"]["serial"]
            new_serial = snapshots["differences"]["added"]["serial"]
            self.log_info(f"{changed_object} serial has been changed from {old_serial} to {new_serial}")

            # Check the new serial is valid and revert if necessary
            if not self.validate_serial(new_serial):
                changed_object.serial = old_serial
                changed_object.save()
                self.log_info(f"{changed_object} serial {new_serial} was not valid. Reverted to {old_serial}")

            self.log_success(message=f"Serial validation completed for {changed_object}")

    def validate_serial(self, serial):
        # add business logic to validate serial
        return False
```

### The `receive_job_hook()` Method

All `JobHookReceiver` subclasses must implement a `receive_job_hook()` method. This method accepts three arguments:

1. `change` - An instance of `nautobot.extras.models.ObjectChange`
2. `action` - A string with the action performed on the changed object ("create", "update" or "delete")
3. `changed_object` - An instance of the object that was changed, or `None` if the object has been deleted
