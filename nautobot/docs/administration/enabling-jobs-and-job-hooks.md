# Enabling Jobs and Job Hooks

## Enabling Jobs

By default when a Job is installed into Nautobot it is installed in a disabled state. In order to enable a Job:

* Navigate to Jobs > Jobs menu
* Select a job that has been installed
* Select **Edit** button
* In the second section titled _Job_, select the **Enabled** checkbox
* Select **Update** button at the bottom

## Enabling Job Hooks

Job hooks are enabled in a similar fashion, but by using the _default_ filters when navigating to the Jobs page the Job Hooks will not be visible. To enable job hooks:

* Navigate to Jobs > Jobs menu
* Select the **Filter** button to bring up the Filter Jobs context
* Look for **Is job hook receiver** and change the drop down to **Yes**
* Select **Apply** button
* Select a job that has been installed
* Select **Edit** button
* In the second section titled _Job_, select the **Enabled** checkbox
* Select **Update** button at the bottom
