# Extras

## Replace Role Related Models with Generic Role Model

Narrowly defined role models including `dcim.DeviceRole`, `dcim.RackRole` and `ipam.Role` are replaced by a generic `extras.Role` model. If any of your models are using the replaced role models, it is required for you to remove the `role` field from your model and add either `nautobot.extras.models.roles.RoleModelMixin` or `nautobot.extras.models.roles.RoleRequiredRoleModelMixin` to your model class definition. `RoleModelMixin` adds a nullable `role` field whereas `RoleRequiredRoleModelMixin` adds a required `role` field. Please go [here](../../core/role-internals.md) to check out how the `extras.Role` model works in v2.0.

## Updates to Job and Job related models

### Job Model Changes

See details about the fundamental changes to `Job` Model [here](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#job-database-model-changes)

### Job Logging Changes

Job logging is now handled by a logger off the Job itself and has a function for each level to send the message (info, warning, debug, etc). There is no longer a `log_success` or `log_failure` function. Checkout the changes in detail [here](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#logging-changes)

### JobResult Model Changes

`JobResult` no longer needs a `job_id`, `user`, or `obj_type` passed to it. It now needs a `name`, `task_name`, and a `worker`. See [here](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#jobresult-database-model-changes) for details.

## Update CustomField, ComputedField, and Relationship

In accordance with the removal of `slug` field in Nautobot v2.0, `CustomField`, `ComputeField` and `Relationship`'s `slug` field is replaced by the `key` field which contains a GraphQL-safe string that is used exclusively in the API and GraphQL. Their `label` fields are now used for display purposes only in the UI. Please go to their respective documentations for more information [CustomField](../../../user-guide/feature-guides/custom-fields.md), [ComputedField](../../../user-guide/platform-functionality/computedfield.md), and [Relationship](../../../user-guide/feature-guides/relationships.md).
