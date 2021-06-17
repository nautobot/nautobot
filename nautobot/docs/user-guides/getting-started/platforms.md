# Platforms

A Platform object can hold various information about a device, such as the OS, OS version, and NAPALM driver.

Further information is available in the [Platforms](https://nautobot.readthedocs.io/en/latest/models/dcim/platform/) section of the Nautobot docs.

While use of Platforms is optional, they provide great value in many use cases.

To add a Platform:

1. Click on **Devices** in the top navigation menu
2. Find **Platforms** and click on the `+` icon in the menu
   
Once on the the `Add a new platform` form:

3. Provide a Name (required)
4. The Slug will auto-populate based on the Name you provide; you may override this if necessary
5. Select a Manufacturer from the drop-down selector (optional)
6. Provide the name of the NAPALM driver (optional) (Note: this must be the exact name of the NAPALM driver)
7. Provide NAPALM arguments (optional)
8. Provide description (optional)
9. Click on the `Create` button

!!! tip 
    NAPALM Driver Options include:
    - eos (Arista)
    - ios (Cisco)
    - nxos (used with `nxapi` feature)
    - nxos_ssh (used for ssh login)
    - junos 

![](../images/getting-started-nautobot-ui/10-add-platform.png)

Once completed, you will be sent to the Platforms page, where all the Platform variants are shown.

!!! tip
    Different use cases for Platforms may require different information. For example, to use a specific Platform with 
    the **Device Onboarding Plugin**, you may be required to override the default Slug value with that of the 
    Netmiko [device_type](https://github.com/ktbyers/netmiko/blob/2dc032b64c3049d3048966441ee30a0139bebc81/netmiko/ssh_autodetect.py#L50)

![](../images/getting-started-nautobot-ui/11-platforms-page.png)
