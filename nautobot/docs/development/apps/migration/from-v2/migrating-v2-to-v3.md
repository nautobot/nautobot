# Migrating v2.x to v3.0

Most migrations outside of the UI updates are minimal. However, for completeness, we will review the UI changes and several niche changes that may affect your app.

## UI Migrations

Nautobot v3.0 introduces many modernizations and improvements to building user interfaces. Although we did our best to make the migration as smooth as possible for app developers, we were not able to avoid some of the **breaking changes**. Below is a list of guides explaining how to upgrade respective UI parts.

Overall, there are three pillars of v3.0 UI:

1. [Introduction of UI component framework.](../ui-component-framework/index.md)
2. [Bootstrap v3.4.1 to v5.x upgrade.](./upgrading-from-bootstrap-v3-to-v5.md)
3. [New Nautobot custom UI APIs.](./new-nautobot-custom-ui-apis.md)

Remember to follow our [UI Best Practices](../../../core/ui-best-practices.md).

## Data Validation Engine

_How to know if you need to make changes?_

Search or grep for `DataComplianceRule` or `ComplianceError`. If there are no matches, you can safely skip this section.

The Data Compliance feature set from the Data Validation Engine App has been moved directly into core. Import paths that reference `nautobot_data_validation_engine.custom_validators.DataComplianceRule` or `nautobot_data_validation_engine.custom_validators.ComplianceError` should be updated to `nautobot.apps.models.DataComplianceRule` and `nautobot.apps.models.ComplianceError`, respectively.

## GraphQL

_How to know if you need to make changes?_

Search or grep for `execute_query` or `execute_saved_query`. If there are no matches, you can safely skip this section.

Code that calls the GraphQL `execute_query()` and `execute_saved_query()` functions may need to be updated to account for changes to the response object returned by these APIs. Specifically, the `response.to_dict()` method is no longer supported, but instead the returned data and any errors encountered may now be accessed directly as `response.data` and `response.errors` respectively.
