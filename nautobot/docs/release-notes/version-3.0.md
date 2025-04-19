# Nautobot v3.0

This document describes all new features and changes in Nautobot 3.0.

## Upgrade Actions

### Job Authors & App Developers

- The Data Compliance feature set from the Data Validation Engine App has been moved directly into core. Import paths that reference `nautobot_data_validation_engine.custom_validators.DataComplianceRule` or `nautobot_data_validation_engine.custom_validators.ComplianceError` should be updated to `nautobot.apps.models.DataComplianceRule` and `nautobot.apps.models.ComplianceError`, respectively.
- Code that calls the GraphQL `execute_query()` and `execute_saved_query()` functions may need to be updated to account for changes to the response object returned by these APIs. Specifically, the `response.to_dict()` method is no longer supported, but instead the returned data and any errors encountered may now be accessed directly as `response.data` and `response.errors` respectively.

## Release Overview

### Added

#### Data Validation Engine

The Nautobot Data Validation Engine functionality previously provided as a separate Nautobot App has been migrated into Nautobot as a core feature. (...TODO provide more details here...)

### Dependencies

#### GraphQL and GraphiQL Updates

The underlying GraphQL libraries (`graphene`, `graphene-django`, `graphene-django-optimizer`) used by Nautobot have been updated to new major versions, including a new major version of the GraphiQL UI. For the most part this upgrade will be seamless to end users, but the response object returned by Nautobot's `execute_query()` and `execute_saved_query()` Python APIs has changed type -- see [Upgrade Actions](#upgrade-actions) above for specifics.

Additionally, this upgrade has changed the GraphQL implementation of two specific classes of Nautobot data filters. The `type` filter available on certain data types in the UI and REST API is now supported by that same name in GraphQL (in Nautobot 2.x and earlier, due to technical limitations, it had to be referenced as `_type`). Conversely, data types that support a `description` filter in the UI and REST API must now, due to technical limitations, refer to the filter as `_description` in GraphQL queries.

#### Added Python 3.13 Support and Removed Python 3.9 Support

As Python 3.9 has reached end-of-life, Nautobot 3.0 requires a minimum of Python 3.10. Python 3.13 support was added.
