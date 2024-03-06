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
location: Cloud "Location
platform: cisco_meraki
```

### Controller Device Group

```yaml
controller_device_group:
  - name: campus
    controller: Panorama1
    tags:
      - high_security
    member_devices:
      - dal-fw01
      - chi-fw01
  - name: dc
    controller: Panorama1
    tags:
      - medium_security
    member_devices:
      - nyc-fw99
      - jcy-fw99
```
