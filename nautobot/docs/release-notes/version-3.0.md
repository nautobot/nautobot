# Nautobot v3.0

This document describes all new features and changes in Nautobot 3.0.

## Upgdate Actions

### Job Authors & App Developers

- The Data Compliance feature set from the Data Validation Engine App has been moved directly into core. Import paths that reference `nautobot_data_validation_engine.custom_validators.DataComplianceRule` or `nautobot_data_validation_engine.custom_validators.ComplianceError` should be updated to `nautobot.apps.models.DataComplianceRule` and `nautobot.apps.models.ComplianceError`, respectively.
