# Jobhooks

A jobhook is a mechanism for automatically starting a job when an object is changed. Jobhooks are similar to [webhooks](../models/extras/webhook.md) except change events initiate a `JobHookReceiver` job instead of a web request. Jobhooks are configured in the web UI under Jobs > Jobhooks.

## Jobhook receivers

Jobhooks are only able to initiate a specific type of job called a jobhook receiver. These are jobs that subclass the `nautobot.extras.jobs.JobHookReceiver` class. Jobhook receivers are similar to normal jobs except they are hard coded to accept only an `object_change` [variable](jobs.md#variables). Jobhook receivers are hidden from the UI by default but are otherwise identical to any other job.

!!! important
    To prevent negatively impacting system performance through an infinite loop, a change that was made by a jobhook receiver job will not trigger another jobhook receiver job to run.

### Example jobhook receiver

```py
from nautobot.extras.jobs import JobHookReceiver
class TestJobHooksJob(JobHookReceiver):
    def run(self, data, commit):
        change_action = data["object_change"].action
        changed_object = data["object_change"].changed_object
        self.log_success(message=f"{change_action} detected for object {changed_object.name}")
```
