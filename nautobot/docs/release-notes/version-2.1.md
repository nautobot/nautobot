# Nautobot v2.1

This document describes all new features and changes in Nautobot 2.1.

## Release Overview

### Added

#### Job file outputs ([#3352](https://github.com/nautobot/nautobot/issues/3352))

The `Job` base class now includes a [`create_file(filename, content)`](../development/jobs/index.md#file-output) method which can be called by a Job to create a persistent file with the provided content when run. This file will be linked from the Job Result detail view for subsequent download by users.

!!! info
    The specific storage backend used to retain such files is controlled by the [`JOB_FILE_IO_STORAGE`](../user-guide/administration/configuration/optional-settings.md#job_file_io_storage) settings variable. The default value of this setting uses the Nautobot database to store output files, which should work in all deployments but is generally not optimal and better alternatives may exist in your specific deployment. Refer to the documentation link above for more details.

#### External Integration Model ([#4694](https://github.com/nautobot/nautobot/issues/4694))

A new [`ExternalIntegration` model](../user-guide/platform-functionality/externalintegration.md) has been added which provides a centralized store for data such as URLs and credentials that are used to access systems external to Nautobot. This information can then be used by jobs or apps to perform actions such as creating DNS records or updating configuration management tickets.

<!-- towncrier release notes start -->
