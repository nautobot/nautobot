# Migrating v2.x to v3.0

Most migrations outside of the UI updates are minimal. However, for completeness, we will review the UI changes and several niche changes that may affect your app. As a high level, you can safely skip these steps if you:

- Do not have any custom apps
- Do have custom apps and can run `nautobot-migrate-bootstrap-v3-to-v5 <path> --dry-run` with no changes and do not have any HTML in Python files.
- Do have custom apps and can run `nautobot-migrate-deprecated-templates <path> --dry-run` with no changes.
- Do have custom apps and can run `pylint --disable=all --enable=nb-deprecated-class --load-plugins=pylint_nautobot --rcfile=/dev/null <path>` with no errors.
- Do have custom apps and do not have a reference to `DataComplianceRule` or `ComplianceError` in your code.
- Do have custom apps and do not have a reference to `execute_query` or `execute_saved_query` in your code.
- Can run `nautobot-server validate_models extras.dynamicgroup` with no output.
- Do not use the REST API (minor change if using pynautobot required to keep same behavior).

More detailed documentation for each of these checks is provided in the next section.
