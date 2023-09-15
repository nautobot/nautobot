# Migrating from 1.x to 2.0

This document provides guidance on migrating code from version 1.x to version 2.0.0. It covers the major changes introduced in the new version and outlines the necessary modifications you need to make in your code to ensure compatibility.

## Table of Contents

- New to Nautobot v2.0.0
    - [New UI](../../core/react-ui.md)
    - [Enhanced Filter Fields](../../../release-notes/version-2.0.md#enhanced-filter-fields-2804)
- Changes to Nautobot in v2.0.0
    - [Generic Role Model](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#generic-role-model)
    - [Collapse Site and Region into Location](../migration/model-updates/dcim.md#replace-site-and-region-with-location-model)
    - [Aggregate model Migrated to Prefix](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#aggregate-migrated-to-prefix)
    - [Renamed Database Foreign Keys and Related Names](../../../release-notes/version-2.0.md#renamed-database-foreign-keys-and-related-names-2520)
    - [Renamed Filter Fields](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#renamed-filter-fields)
    - [Corrected Filter Fields](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#corrected-filter-fields)
    - [Jobs](../../jobs/migration/from-v1.md)
- Steps to Migrate an App from V1
    - Preliminary Steps:
        - Add [`pylint-nautobot`](https://github.com/nautobot/pylint-nautobot) as a development dependency
        - Run `pylint -v --disable=all --enable=nautobot-code-location-changes,nautobot-replaced-models *` in order to parse your development environment for changes that need to be fixed before pylint-django can successfully run.
        - Specific steps to install and run `pylint-nautobot` in your development environment is available [here](https://docs.nautobot.com/projects/pylint-nautobot/en/latest/getting_started/)
    - [Dependency Updates](dependency-updates.md)
        - [Nautobot Version](dependency-updates.md#nautobot-version)
        - [Python Version](dependency-updates.md#python-version)
        - [pylint-nautobot](dependency-updates.md#pylint-nautobot)
    - [Code Updates](code-updates.md)
        - [Update Code Import Locations](code-updates.md#update-code-import-locations)
        - [Replace PluginMenuItem with NavMenuItem](code-updates.md#replace-pluginmenuitem-with-navmenuitem)
        - [Replace DjangoFilterBackend with NautobotFilterBackend](code-updates.md#replace-djangofilterbackend-with-nautobotfilterbackend)
        - [Revamp Rest API Serializers](code-updates.md#revamp-rest-api-serializers)
        - [Revamp CSV Import and Export](code-updates.md#revamp-csv-import-and-export)
    - Model Updates
        - [Global](model-updates/global.md)
            - [Replace the Usage of Slugs with Composite Keys](model-updates/global.md#replace-the-usage-of-slugs-with-composite-keys)
        - [DCIM](model-updates/dcim.md)
            - [Replace Site and Region with Location Model](model-updates/dcim.md#replace-site-and-region-with-location-model)
        - [Extras](model-updates/extras.md)
            - [Replace Role Related Models with Generic Role Model](model-updates/extras.md#replace-role-related-models-with-generic-role-model)
            - [Update Job and Job related models](model-updates/extras.md#update-job-and-job-related-models)
                - [Job Model Changes](model-updates/extras.md#job-model-changes)
                - [Job Logging Changes](model-updates/extras.md#job-logging-changes)
                - [JobResult Model Changes](model-updates/extras.md#jobresult-model-changes)
            - [Update CustomField, ComputedField, and Relationship](model-updates/extras.md#update-customfield-computedfield-and-relationship)
        - [IPAM](model-updates/ipam.md)
            - [Replace Aggregate with Prefix](model-updates/ipam.md#replace-aggregate-with-prefix)
            - [Introduction of Namespace](model-updates/ipam.md#introduction-of-namespace)
            - [Concrete Relationship between Prefix and IP Address](model-updates/ipam.md#concrete-relationship-between-prefix-and-ip-address)
            - [Concrete Relationship between Prefix and Self](model-updates/ipam.md#concrete-relationship-between-prefix-and-self)
            - [Convert Relationship Type between Prefix and VRF to Many to Many](model-updates/ipam.md#convert-relationship-type-between-prefix-and-vrf-to-many-to-many)
