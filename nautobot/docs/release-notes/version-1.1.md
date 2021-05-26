# Nautobot v1.1

This document describes all new features and changes in Nautobot 1.1.

## Release Overview

### Added

#### GraphQL ORM Functions

Two new [GraphQL utility functions](../plugins/development.md) have been added to allow easy access to the GraphQL system from source code. Both can be access throughout Nautobot and plugins by using `from nautobot.core.graphql import execute_saved_query, execute_query`.

1) `execute_query()`: Runs string as a query against GraphQL.
2) `execute_saved_query()`: Execute a saved query from Nautobot database.

#### Saved GraphQL Queries

[Saved GraphQL queries](../additional-features/graphql.md) offers a new model where reusable queries can be stored in Nautobot. New views have been create for entering data and modifcations to the original GraphiQL interface to allow populating the interface, editing and saving new queries.

Saved queries can easily be imported into the GraphiQL interface by using the new navigation tab located on the right side of the navbar. Inside the new tab are also buttons for editing and saving queries directly into Nautobot's databases.
