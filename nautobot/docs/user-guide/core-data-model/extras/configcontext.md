# Configuration Contexts

Sometimes it is desirable to associate additional data with a group of devices or virtual machines to aid in automated configuration. For example, you might want to associate a set of syslog servers for all devices within a particular region. Context data enables the association of extra user-defined data with devices and virtual machines grouped by one or more of the following assignments:

* Location
* Role
* Device type
* Device redundancy group
* Platform
* Cluster group
* Cluster
* Tenant group
* Tenant
* Tag
* Dynamic group - Need to set `settings.CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED` to `True`. [See notes here](../../administration/configuration/settings.md#config_context_dynamic_groups_enabled)

Context data not specifically assigned to one or more of the above groups is by default associated with **all** devices and virtual machines.

Configuration contexts may be managed within Nautobot via the UI and/or API; they may also be managed externally to Nautobot in a Git repository if desired.

## Hierarchical Rendering

=== "List Elements"

    When the data schema is a dictionary where the value of the data is a list, the rendering is more of a merge/overwrite.

    Context data is arranged hierarchically, so that data with a higher weight can be entered to override lower-weight data. Multiple instances of data are automatically merged by Nautobot to present a single dictionary for each object.

    For example, suppose we want to specify a set of syslog and NTP servers for all devices within a region. We could create a config context instance with a weight of 1000 assigned to the region, with the following JSON data:

    ```json
    {
        "ntp-servers": [
            "172.16.10.22",
            "172.16.10.33"
        ],
        "syslog-servers": [
            "172.16.9.100",
            "172.16.9.101"
        ]
    }
    ```

    But suppose there's a problem at one particular location preventing traffic from reaching the regional syslog server. Devices there need to use a local syslog server instead of the two defined above. We'll create a second config context assigned only to that site with a weight of 2000 and the following data:

    ```json
    {
        "syslog-servers": [
            "192.168.43.107"
        ]
    }
    ```

    When the context data for a device at this location is rendered, the second, higher-weight data overwrite the first, resulting in the following:

    ```json
    {
        "ntp-servers": [
            "172.16.10.22",
            "172.16.10.33"
        ],
        "syslog-servers": [
            "192.168.43.107"
        ]
    }
    ```

    Data from the higher-weight context overwrites conflicting data from the lower-weight context, while the non-conflicting portion of the lower-weight context (the list of NTP servers) is preserved.

=== "Dictionary Elements"

    When the data schema is a dictionary where the value of the data is another dictionary, the rendering is more of a merge/additive functionality.

    Context data is arranged hierarchically, so that data with a higher weight can be entered to override lower-weight data. Multiple instances of data are automatically merged by Nautobot to present a single dictionary for each object.

    For example, suppose we want to specify a set of syslog and NTP servers for all devices within a region. We could create a config context instance with a weight of 1000 assigned to the region, with the following JSON data:

    ```json
    {
        "ntp-servers": {
            "172.16.10.22": {},
            "172.16.10.33": {}
        },
        "syslog-servers": {
            "172.16.9.100": {},
            "172.16.9.101": {}
        }
    }
    ```

    But suppose that one particular location also has their own regional syslog server. Devices there need to use a local syslog server as well as the two defined above. We'll create a second config context assigned only to that site with a weight of 2000 and the following data:

    ```json
    {
        "syslog-servers": {
            "192.168.43.107": {}
        }
    }
    ```

    When the context data for a device at this location is rendered, the second, higher-weight data is merged with the first, resulting in the following:

    ```json
    {
        "ntp-servers": {
            "172.16.10.22": {},
            "172.16.10.33": {}
        },
        "syslog-servers": {
            "172.16.9.100": {},
            "172.16.9.101": {},
            "192.168.43.107": {}
        }
    }
    ```

    Data from the higher-weight context is deepmerged with the lower-weight context, while the non-conflicting portion of the lower-weight context (the list of NTP servers) is preserved. In this context the weights matter, as they dictate the ordering into the deepmerge.

!!! warning
    ConfigContexts can be applied to parents and descendants of TreeModels such as Locations and RackGroups. The inheritance of ConfigContext will always be determined by the value of the weight attribute. You may see unexpected behavior if you have ConfigContexts of the same weight applied to TreeModel parents and their descendants.

## Local Context Data

Devices and virtual machines may also have a local config context defined. This local context will _always_ take precedence over any separate config context objects which apply to the device/VM. This is useful in situations where we need to call out a specific deviation in the data for a particular object.

!!! warning
    If you find that you're routinely defining local context data for many individual devices or virtual machines, custom fields may offer a more effective solution.
