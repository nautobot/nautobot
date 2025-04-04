# Wireless

The goal of the Wireless Models is to enable Day-2 Wireless Workflows and Automation focusing on Campus networks. The following use-cases are covered:

1. Inventory of SSID's through the use of [Wireless Networks](wirelessnetwork.md)
2. Grouping Access Points through the use of [Controller Managed Device Group](../dcim/controllermanageddevicegroup.md)
3. Represent common radio frequency and other wireless physical settings through [Radio Profiles](radioprofile.md)

Currently not implemented is support for Wireless or Microwave backhaul, WISP, 5G or LTE.

## Entity Relationship Diagram

This schema illustrates the connections between related models.

```mermaid
---
title: Wireless Entity Relationship Diagram
---
erDiagram
    ControllerManagedDeviceGroup {
        string name UK
        Device devices FK
        Controller controller FK
        ControllerManagedDeviceGroup parent FK
        RadioProfile radio_profiles FK
        WirelessNetwork wireless_networks FK
    }

    WirelessNetwork {
        string name UK
        string ssid
        string description
        string mode
        boolean enabled
        string authentication
        SecretsGroup secrets_group FK
        boolean hidden
        Prefix prefixes FK
        ControllerManagedDeviceGroup controller_managed_device_groups
    }

    SupportedDataRate {
        string standard UK
        int rate UK
        int mcs_index
        RadioProfile radio_profiles FK
    }

    RadioProfile {
        string name UK
        string frequency
        int tx_power_min
        int tx_power_max
        array channel_width
        array allowed_channel_list
        SupportedDataRate supported_data_rates FK
        string regulatory_domain
        int rx_power_min
    }

    Device {
        string name UK
        ControllerManagedDeviceGroup controller_managed_device_group FK
        Interface interfaces FK
    }

    Interface {
        string name UK
        Device device FK
        VLAN tagged_vlans FK
        VLAN untagged_vlan FK
    }

    ControllerManagedDeviceGroupWirelessNetworkAssignment {
        ControllerManagedDeviceGroup controller_managed_device_group_assignment FK
        WirelessNetwork wireless_network_assignment FK
        VLAN vlan FK
    }

    VLAN {
        int vid
        string name
        Interface interfaces
        ControllerManagedDeviceGroupWirelessNetworkAssignment controller_managed_device_group_wireless_network_assignments FK
    }
    Controller {
        string name UK
        ControllerManagedDeviceGroup controller_managed_device_groups FK
    }
    SecretsGroup {
        string name UK
        Secret secrets FK
        WirelessNetwork wireless_networks FK
    }
    

    ControllerManagedDeviceGroup ||--o{ Controller : has
    ControllerManagedDeviceGroup }o--o{ RadioProfile : "through ControllerManagedDeviceGroupRadioProfileAssignment"
    ControllerManagedDeviceGroup }o--|| Device : "has"
    ControllerManagedDeviceGroup }o--o{ ControllerManagedDeviceGroupWirelessNetworkAssignment : has
    WirelessNetwork }o--o{ ControllerManagedDeviceGroupWirelessNetworkAssignment : has
    WirelessNetwork }o--o{ SecretsGroup : has
    ControllerManagedDeviceGroupWirelessNetworkAssignment ||--o{ VLAN : has

    RadioProfile }o--o{ SupportedDataRate : has

    Device }o--o{ Interface : has
    Interface }o--o{ VLAN : has 
```
