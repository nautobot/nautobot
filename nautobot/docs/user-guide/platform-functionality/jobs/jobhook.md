# Job Hooks

A Job Hook is a mechanism for automatically starting a [job](./index.md) when an object is changed. Job Hooks are similar to [webhooks](../webhook.md) except that an object change event initiates a `JobHookReceiver` job instead of a web request. Job hooks are configured in the web UI under **Jobs > Job Hooks**.

## Configuration

* **Name** - A unique name for the job hook.
* **Content type(s)** - The type or types of Nautobot object that will trigger the job hook.
* **Job** - The [job hook receiver](../../../development/jobs/job-extensions.md#job-hook-receivers) that this job hook will run.
* **Enabled** - If unchecked, the job hook will be inactive.
* **Events** - A job hook may trigger on any combination of create, update, and delete events. At least one event type must be selected.

For any Job that is loaded into Nautobot, the Job must be enabled to run. See [Enabling Jobs for Running](./managing-jobs.md#enabling-and-disabling-jobs) for more details.
