# Nautobot v3.3

This document describes all new features and chagnes in Nautobot 3.3.

## Upgrade Actions

### Administrators

TODO

## Release Overview

### Added

TODO

### Changed

TODO

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
