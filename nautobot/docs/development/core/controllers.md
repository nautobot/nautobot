# Controllers

Controllers in Nautobot enable users to model a set of industry-standard network or SDN controllers, along with their relationships to the devices they manage.

## Use Cases

These models support the representation of various use cases, including, but not limited to:

- Cisco ACI
- Panorama
- Juniper MIST
- Arista CloudVision
- Meraki
- Wireless Controllers (e.g., Ruckus, Cisco)
- OpenStack

Using controllers enables answering inventory-related queries:

- Find the controller for the given device group.
- Find the controller for the given device.
- List device groups managed by the controller.
- List devices managed by the controller.

## Controller Model

Represents an entity that manages or controls one or more devices, acting as a central point of control.

A Controller can be deployed to a single device or a group of devices represented by single `DeviceRedundancyGroup`.

## Controller Device Group Model

Represents a mapping of controlled devices to a specific controller.

This model allows for the organization of controlled devices into hierarchical groups for structured representation.

## Entity Relationship Diagram

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

## Examples

### Cisco ACI

```yaml
name: Cisco ACI APIC - east
deployed_controller_device: DC-East-APIC-1
location: DC-East
platform: cisco_apic
```

### Cisco Meraki

```yaml
name: Cisco Meraki SAAS
deployed_controller_device: ~
location: Cloud Location
platform: cisco_meraki
```

### Controller Device Group

```yaml
controller_device_group:
  - name: campus
    controller: Panorama1
    tags:
      - high_security
    devices:
      - dal-fw01
      - chi-fw01
  - name: dc
    controller: Panorama1
    tags:
      - medium_security
    devices:
      - nyc-fw99
      - jcy-fw99
```
