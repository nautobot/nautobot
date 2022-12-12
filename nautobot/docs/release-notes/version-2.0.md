<!-- markdownlint-disable MD024 -->

# Nautobot v2.0

This document describes all new features and changes in Nautobot 2.0.

If you are a user migrating from Nautobot v1.X, please refer to the ["Upgrading from Nautobot v1.X"](../installation/upgrading-from-nautobot-v1.md) documentation.

## Release Overview

### Added

#### Added Site Fields to Location ([#2954](https://github.com/nautobot/nautobot/issues/2954))

Added Site Model Fields to Location. Location Model now has `asn`, `comments`, `contact_email`, `contact_name`, `contact_phone`, `facility`, `latitude`, `longitude`, `physical_address`, `shipping_address` and `time_zone` fields.

### Changed

#### Collapse Region and Site Models into Location ([#2517](https://github.com/nautobot/nautobot/issues/2517))

### Removed

<!-- towncrier release notes start -->
