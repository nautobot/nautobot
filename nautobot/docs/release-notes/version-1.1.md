# Nautobot v1.1

This document describes all new features and changes in Nautobot 1.1

Users migrating from NetBox to Nautobot should also refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation as well.

## Release Overview

### Added

#### GraphQL ORM Functions

Two new [GraphQL utility functions](../plugins/development.md) have been added to allow easy access to the GraphQL system from source code. Both can be accessed by using `from nautobot.core.graphql import execute_saved_query, execute_query`.

1) `execute_query()`: Runs string as a query against GraphQL.
2) `execute_saved_query()`: Execute a saved query from Nautobot database.

#### Read Only Jobs [#200](https://github.com/nautobot/nautobot/issues/200)

Jobs may be optionally marked as read only by setting the `read_only = True` meta attribute. This prevents the job from making any changes to nautobot data and suppresses certain log messages. Read only jobs can be a great way to safely develop new jobs, and for working with reporting use cases. Please see the [Jobs documentation](https://nautobot.readthedocs.io/en/latest/additional-features/jobs/) for more details.

#### Saved GraphQL Queries [#3](https://github.com/nautobot/nautobot/issues/3)

[Saved GraphQL queries](../additional-features/graphql.md#saved-queries) offers a new model where reusable queries can be stored in Nautobot. New views for managing saved queries are available; additionally, the GraphiQL interface has been augmented to allow populating the interface from a saved query, editing and saving new queries.

Saved queries can easily be imported into the GraphiQL interface by using the new navigation tab located on the right side of the navbar. Inside the new tab are also buttons for editing and saving queries directly into Nautobot's databases.

### Changed

### Removed
