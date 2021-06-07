# Nautobot v1.1

This document describes all new features and changes in Nautobot 1.1

Users migrating from NetBox to Nautobot should also refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation as well.

## Release Overview

### Added

#### Read Only Jobs [#200](https://github.com/nautobot/nautobot/issues/200)

Jobs may be optionally marked as read only by setting the `read_only = True` meta attribute. This prevents the job from making any changes to nautobot data and suppresses certain log messages. Read only jobs can be a great way to safely develop new jobs, and for working with reporting use cases. Please see the [Jobs documentation](https://nautobot.readthedocs.io/en/latest/additional-features/jobs/) for more details.

### Changed

### Removed
