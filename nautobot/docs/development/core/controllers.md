# Controllers

A Controller in Nautobot is an abstraction meant to represent network or SDN (Software-Defined Networking) controllers. These may include, but are not limited to, wireless controllers, cloud-based network management systems, and other forms of central network control mechanisms.

For more details, refer to the user guide for a [Controller model](../../user-guide/core-data-model/dcim/controller.md) or a [Controller Device Group model](../../user-guide/core-data-model/dcim/controllerdevicegroup.md).

## Entity Relationship Diagram

This schema illustrates the connections between related models.

```mermaid
---
title: Controllers Entity Relationship Diagram
---
erDiagram

    Platform {
        string name UK
        Manufacturer manufacturer FK
        string network_driver
        string napalm_driver
        json napalm_args
        string description
    }

    SoftwareVersion {
        Platform platform FK
        string version
        string alias
        date release_date
        date end_of_support_date
        url documentation_url
        boolean long_term_support
        boolean pre_release
        Status status FK
    }

    Device {
        DeviceType device_type FK
        ControllerDeviceGroup controller_device_group FK
        DeviceRedundancyGroup device_redundancy_group FK

        string name UK
        Status status FK
        Role role FK
        Tenant tenant FK
        Platform platform FK
        SoftwareVersion software_version FK
        string serial
        string asset_tag UK
        Location location FK
        IPAddress primary_ip4 FK
        IPAddress primary_ip6 FK
        int device_redundancy_group_priority
        SecretsGroup secrets_group FK
    }

    DeviceRedundancyGroup {
        string name UK
        Status status FK
        string description
        string failover_strategy
        SecretsGroup secrets_group FK
    }

    Controller {
        Device deployed_controller_device FK "Nullable"
        DeviceRedundancyGroup deployed_controller_group FK "Nullable"

        string name UK
        Status status FK
        Role role FK
        Tenant tenant FK
        string description
        Platform platform FK
        ExternalIntegration external_integration FK
        Location location FK
    }

    ControllerDeviceGroup {
        ControllerDeviceGroup parent FK "Nullable"
        Controller controller FK

        string name UK
        int weight
    }

    ControllerDeviceGroup ||--o{ ControllerDeviceGroup : "contains children"
    Controller }o--|| ControllerDeviceGroup : "controls Devices in"
    Controller }o--|| DeviceRedundancyGroup : "can be deployed to"
    Device }o--|| SoftwareVersion : "runs"
    Controller }o--|| Platform : "runs"
    Controller }o--|| Device : "can be deployed to"
    Device }o--|| ControllerDeviceGroup : "can be member of"
    Device }o--|| DeviceRedundancyGroup : "can be member of"
    Platform ||--o{ SoftwareVersion : "has"
```
