# Impact Analysis

Upgrading to Nautobot v3.0 introduces many changes to the UI, but the upgrade process is designed to minimize disruption. For administrators, most day-to-day workflows remain intact without changes. Developers will find that the primary changes are in bootstrap migrations, which will largely be handled by the upgrade tooling.

At a high-level overview, consider the following impacting changes:

| Type                   | Description                                                             | Impact                     |
|------------------------|-------------------------------------------------------------------------|----------------------------|
| Filter Fields          | Changes to filter fields                                                | 🟠 May require updates to API queries, Dynamic Groups, Permissions, and Saved Views. Tooling is provided to assist with updates. |
| Default to Exclude M2M | API now defaults to exclude many-to-many relationships unless specified | 🟠 Minor adjustments using pynautobot or API calls may require adjustments.              |
| Jobs Approval Process  | Updates to job approval process to use Workflow Approvals               | 🟢 Minor changes; see details below for updated permissions and workflow.                |
| GraphiQL               | Upgrade to Graphene V3                                                  | 🟢 No impact for most UI or API users; those using internal APIs may notice differences. |
| Authorized Docs        | Documentation now requires user authorization                           | 🟢 No functional impact for users with logins.                                           |
| Data Validation        | Nautobot Data Validation App has migrations to Nautobot Core            | 🟢 Data will be migrated during standard Django Migrations, no functional impact.        |

Legend: 🟢 Low impact 🟠 Medium impact

## Filter Fields

TODO: Follow up

## Default to Exclude M2M

In Nautobot 3.0, API endpoints now exclude many-to-many (M2M) relationship fields (except for `tags`, `content_types`, and `object_types`) by default in their responses. This change helps improve performance and reduces unnecessary data transfer. If your integrations or scripts rely on M2M fields being present in API responses, you will need to explicitly request these fields using the `exclude_m2m=False` query parameter.

- **Direct API consumers:** Update your API queries to include M2M fields as needed. For example: `http://nautobot.example.com/api/dcim/devices/?exclude_m2m=False`.
- **pynautobot users (v3.0.0+):** Add `exclude_m2m=False` to an individual request (`nb.dcim.devices.all(exclude_m2m=False)`) or set the default for all requests to pynautobot (`import pynautobot; nb = pynautobot.api(url, token, exclude_m2m=False)`) to maintain prior behavior.
- **Nautobot Ansible users (v6.0.0+):** There is no change required when using module or inventory plugins. When using a lookup plugin, you will need to use the `api_filters` parameter to include M2M fields. For example: `api_filters='exclude_m2m=False'`.

Review your API usage to ensure that any required M2M fields are explicitly requested after upgrading.

## Jobs Approval Process

Prior to upgrading to Nautobot 3.x, upgrade to at least Nautobot 2.4.15 so that the management command `check_job_approval_status` is available to identify Jobs and Scheduled Jobs that have `approval_required=True`.

- Running the command doesn't approve/run/deny jobs, it just identifies the ones that need such action to be performed as a separate step, namely to run the job or delete the scheduled job.
    - After running this command to identify the impacted Jobs, and completing the upgrade to Nautobot 3.x, you'll want to define appropriate approval workflows to apply to those jobs.
- Job approval permissions have been updated in the UI. Approvers via UI must now be granted the `extras.change_approvalworkflowstage` and `extras.view_approvalworkflowstage` permissions, replacing the previous requirement for `extras.approve_job`. This change aligns with updates to the approval workflow implementation and permissions model. This change does not affect API-based approvals.

## GraphiQL

There is no impact to API and UI users. In addition you no longer have to use `_type` instead of `type` as both are supported for backwards compatibility.

The `execute_query()` and `execute_saved_query()` now return a different class of response object, which will impact Python code that directly calls these methods.

## Data Validation Engine

With Nautobot 3.0, the Data Validation Engine previously provided by a Nautobot App is now integrated into Nautobot Core. This means you no longer need to install or maintain a separate plugin for data validation functionality.

- All existing validation rules and configurations will be automatically migrated during the standard Django migration process.
- There is no change to how validation rules are defined or managed in the UI or API.
- No user action is required unless you have custom integrations that directly referenced the standalone Data Validation App; these should be updated to reference the core functionality instead.

For most users, this change is seamless and does not require any manual intervention.
