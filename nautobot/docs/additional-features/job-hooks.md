# Job hooks

A job hook is a mechanism for automatically starting a [job](./jobs.md) when an object is changed. Job hooks are similar to [webhooks](../models/extras/webhook.md) except change events initiate a `JobHookReceiver` job instead of a web request. Job hooks are configured in the web UI under Jobs > Job Hooks.

## Job hook receivers

Job hooks are only able to initiate a specific type of job called a job hook receiver. These are jobs that subclass the `nautobot.extras.jobs.JobHookReceiver` class. Job hook receivers are similar to normal jobs except they are hard coded to accept only an `object_change` [variable](jobs.md#variables). Job hook receivers are hidden from the jobs listing UI by default but function similarly to other jobs. The job hook receiver class only implements one method called `receive_jobhook`.

!!! important
    To prevent negatively impacting system performance through an infinite loop, a change that was made by a job hook receiver job will not trigger another job hook receiver job to run.

### Example job hook receiver

```py
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.jobs import JobHookReceiver
class ExampleJobHookReceiver(JobHookReceiver):
    def receive_jobhook(self, change, action, changed_object):
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

### The `receive_jobhook()` Method

All job hook receivers must implement a `receive_jobhook()` method. This method accepts three arguments:

1. `change` - An instance of `nautobot.extras.models.ObjectChange`
2. `action` - A string with the action performed on the changed object ("create", "update" or "delete")
3. `changed_object` - An instance of the object that was changed, or `None` if the object has been deleted
