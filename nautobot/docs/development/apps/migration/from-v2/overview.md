# Overview

Most migrations outside of the UI updates are minimal. However, for completeness, we will review the UI changes and several niche changes that may affect your app. As a high level, you can safely skip these steps if you:

| Do not have custom apps **OR** your custom apps meet **all** the following conditions:                                                                                                                                            |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Can run `nautobot-migrate-bootstrap-v3-to-v5 <path> --dry-run` with no changes.                                                                                                                                                   |
| Can run `nautobot-migrate-bootstrap-v3-to-v5 <path> --check-python-files --no-fix-html-templates` with no reports related to HTML in Python files. Note that the algorithm is greedy and occasionally may output false positives. |
| Can run `nautobot-migrate-deprecated-templates <path> --dry-run` with no changes.                                                                                                                                                 |
| Can run `pylint --disable=all --enable=nb-deprecated-class --load-plugins=pylint_nautobot --rcfile=/dev/null <path>` with no errors.                                                                                              |
| Do not have a reference to `DataComplianceRule` or `ComplianceError` in your code.                                                                                                                                                |
| Do not have a reference to `execute_query` or `execute_saved_query` in your code.                                                                                                                                                 |
| Can run `nautobot-server validate_models extras.dynamicgroup extras.savedview` with no output.                                                                                                                                    |
| Do not use the REST API (minor change if using pynautobot required to keep same behavior).                                                                                                                                        |

More detailed documentation for each of these checks is provided in the next section.
