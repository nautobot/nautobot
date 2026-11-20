# Cloud Accounts

Cloud accounts provide a way to track account details for public and private cloud [providers](../dcim/manufacturer.md) (AWS, Azure, GCP, DigitalOcean and OpenStack etc) in Nautobot. A cloud account represents an account with a provider, such as an AWS account, an Azure subscription or a GCP project. Each cloud account must have a name, an account number and a provider, and you may optionally assign a secrets group to it.

The name of each cloud account must be unique per provider, so cloud accounts of different providers may share a name.

Each cloud account must be assigned an operational [`status`](../../platform-functionality/status.md). The following statuses are available by default:

- Planned
- Active
- Decommissioning

A cloud account may optionally be assigned to a [tenant](../tenancy/tenant.md) and to a [cloud account group](./cloudaccountgroup.md), which represents the organization container that the account belongs to, such as an Azure management group, an AWS organizational unit or a GCP folder.

+++ 3.3.0
    The `status`, `tenant` and `cloud_account_group` fields have been added. Existing cloud accounts are set to the "Active" status when upgrading.

+/- 3.3.0
    Cloud account names were previously unique across all providers. They are now unique per provider.
