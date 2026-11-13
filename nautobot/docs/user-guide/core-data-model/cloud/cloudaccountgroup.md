# Cloud Account Groups

+++ 3.3.0

Cloud account groups represent the organization containers that cloud providers place above [cloud accounts](./cloudaccount.md), such as Azure management groups, AWS organizational units or GCP folders. They record where each cloud account sits in the provider's organization hierarchy, so that cloud accounts and the resources in them can be found and filtered by that hierarchy.

Each cloud account group must have a name and must be assigned to a [cloud resource type](./cloudresourcetype.md), which describes the kind of container (for example "Azure Management Group") and the provider it belongs to. Extra configurations can be stored in JSON format in the `extra_config` attribute, and are validated against the config schema of the cloud resource type, if it defines one.

Cloud account groups may optionally be nested within one another through the `parent` field to model a multi-level hierarchy. The name of each cloud account group must be unique within its parent, so groups under different parents may share a name. Top-level cloud account groups, which have no parent, must have names that are unique among themselves.

Each [cloud account](./cloudaccount.md) can optionally be assigned to one cloud account group. When cloud accounts, [cloud resource groups](./cloudresourcegroup.md), [cloud networks](./cloudnetwork.md) or [cloud services](./cloudservice.md) are filtered by `cloud_account_group`, the results include the objects in the selected group and in all of its descendant groups.
