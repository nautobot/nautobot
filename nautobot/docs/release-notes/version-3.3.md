# Nautobot v3.3

This document describes all new features and chagnes in Nautobot 3.3.

## Upgrade Actions

### Administrators

TODO

#### Configure `REST_API_MAX_DEPTH` If Needed

You may wish to audit your logs of existing REST API `GET` requests to see what values of the `depth` query parameter are being used, as the default maximum value of this parameter has been decreased ([see below](#rest-api-maximum-depth-default) If the new default maximum of 2 is too restrictive for your clients' usage, you can configure [`REST_API_MAX_DEPTH`](../user-guide/administration/configuration/settings.md#rest_api_max_depth) to a higher value.

## Release Overview

### Added

TODO

### Changed

TODO

#### REST API Maximum `depth` Default

The default maximum value of a REST API `GET` query `depth` parameter has been decreased from 10 to 2, as higher values tend to be extremely expensive to evaluate and are rarely used in practice. If your deployment needs a higher maximum (up to the previous limit of 10), an administrator can configure the new [`REST_API_MAX_DEPTH`](../user-guide/administration/configuration/settings.md#rest_api_max_depth) as needed.

#### Enhanced Export/Import

The object export/import functionality has been enhanced in several ways:

- JSON and YAML formats are now supported in addition to the existing CSV format support.
- Imports can now update existing records as well as create existing records, when requested ("upsert" functionality).
- CSV export/import now includes a metadata header row, and includes support for a wider range of many-to-many fields.

For more details, refer to the [import and export documentation](../user-guide/feature-guides/import-and-export.md).

### Dependencies

#### Removed Python 3.10 Support

As Python 3.10 is now end-of-life, Nautobot 3.3 has dropped support for Python 3.10.

<!-- pyml disable-num-lines 2 blanks-around-headers -->
<!-- towncrier release notes start -->
