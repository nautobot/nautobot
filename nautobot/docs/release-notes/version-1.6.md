<!-- markdownlint-disable MD024 -->

# Nautobot v1.6

This document describes all new features and changes in Nautobot 1.6.

## Release Overview

### Added

#### Installation Metrics

A new setting, [`INSTALLATION_METRICS_ENABLED`](../configuration/optional-settings.md#installation_metrics_enabled), has been added to allow Nautobot to send anonymous installation metrics to the Nautobot maintainers. This setting is `True` by default but can be changed in `nautobot_config.py` or the `NAUTOBOT_INSTALLATION_METRICS_ENABLED` environment variable.

If the [`INSTALLATION_METRICS_ENABLED`](../configuration/optional-settings.md#installation_metrics_enabled) setting is `True`, running the [`post_upgrade`](../administration/nautobot-server.md#post_upgrade) or [`send_installation_metrics`](../administration/nautobot-server.md#send_installation_metrics) management commands will send a list of all installed [plugins](../plugins/index.md) and their versions, as well as the currently installed Nautobot version to the Nautobot maintainers. A randomized uuid will be generated and saved in the [`DEPLOYMENT_ID`](../configuration/optional-settings.md#deployment_id) setting to anonymously and uniquely identify each installation. The plugin names will be one-way hashed with SHA256 to further anonymize the data sent.

The following is an example of the data that is sent:

```py
{
    "deployment_id": "1de3dacf-f046-4a98-8d4a-17419080db79",
    "nautobot_version": "1.6.0b1",
    "python_version": "3.10.12",
    "installed_apps": {
        "3ffee4622af3aad6f78257e3ae12da99ca21d71d099f67f4a2e19e464453bee7": "1.0.0" # "example_plugin" hashed by sha256
    }
}
```

### Changed

<!-- towncrier release notes start -->
