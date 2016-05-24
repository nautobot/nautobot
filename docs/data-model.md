# DCIM

The data center infrastructure management (DCIM) component of NetBox assists in the management of physical assets within a network: equipment racks, the gear in them, and the cabling that connects it all.

### Sites

A site is a geographic location at which network equipment is housed. How you choose to define sites will depend on the nature of your organization, but typically a site will be a building or campus. For example, a chain of banks might create a site to represent each of its branches, a site for its corporate headquarters, and two additional sites for its presence in two colocation facilities.

### Racks

Within each site exist one or more racks. Each rack within NetBox represents a physical two- or four-post equipment rack in which equipment is mounted. Rack height is measured in *rack units *(U); most racks are between 42U and 48U, but NetBox allows you to define racks of any height. Each rack has two faces (front and rear) on which devices can be mounted.

Each rack is assigned a name and (optionally) a separate facility ID. This is helpful when leasing space in a data center your organization does not own: The facility will often assign a seemingly arbitrary ID to a rack (for example, M204.313) whereas internally you refer to is simply as "R113." The facility ID can alternatively be used to store a rack's serial number.

### Rack Groups

Racks can be arranged into groups. As with sites, how you choose to designate rack groups will depend on the nature of your organization. For example, if each site is a campus, each group might be a building. If each site is a building, each rack group might be a floor or room.

Each group is assigned to a parent site for easy navigation. Hierarchical recursion of rack groups is not currently supported.

### Devices

Every piece of hardware which is installed within a rack exists in NetBox as a device. Devices are measured in rack units (U) and whether they are full depth. 0U devices which can be installed in a rack but don't consume vertical rack space (such as a vertically-mounted power distribution unit) can also be defined.

A device is said to be "full depth" if its installation on one rack face prevents the installation of any other device on the opposite face within the same rack unit(s). This could be either because the device is physically too deep to allow a device behind it, or because the installation of an opposing device would impede air flow.

Each device has a physical device type (make and model), which is discussed below.

### Device Roles

NetBox allows for the definition of arbitrary device roles by which devices can be organized. For example, you might create roles for core switches, distribution switches, and access switches. In the interest of simplicity, device can only belong to one device role.

### Platform

A device's platform is used to denote the type of software running on it. This can be helpful when it is necessary to distinguish between, for instance, different feature sets. Note that two devices of same type may be assigned different platforms: for example, one Juniper MX240 running Junos 14 and another running Junos 15.

The assignment of platforms to devices is an entirely optional feature, and may be disregarded if not desired.

### Modules

A device can be assigned modules which represent internal components. Currently, these are used merely for inventory tracking, although future development might see their functionality expand.

### Device Components

There are five types of device components which comprise all of the interconnection logic with NetBox:

* Console ports
* Console server ports
* Power ports
* Power outlets
* Interfaces

Console ports connect only to console server ports, and power ports connect only to power outlets. Interfaces connect to one another in a symmetric manner: If interface A connects to interface B, interface B therefore connects to interface A. (The relationship between two interfaces is actually represented in the database by an InterfaceConnection object, but this is transparent to the user.)

Each type of connection can be defined as either *planned* or *connected*. This allows for easily denoting connections which have not yet been installed.

In addition to a connecting peer, interfaces are also assigned a form factor and may be designated as management-only (for out-of-band management). Interfaces may also be assigned a short description.

### Device Types

A device type represents a particular manufacturer and model of equipment. Device types describe the physical attributes of a device (rack height and depth), its class (e.g. console server, PDU, etc.), and its individual components (console, power, and data).

### Manufacturers

Each device type belongs to one manufacturer; e.g. Cisco, Opengear, or APC. Manufacturers are used to group different models of device.

### Device Component Templates

Each device type is assigned a number of component templates which describe the console, power, and data ports a device has. These are:

* Console port templates
* Console server port templates
* Power port templates
* Power outlet templates
* Interface templates

Whenever a new device is created, it is automatically assigned console, power, and interface components per the templates assigned to its device type. For example, suppose your network employs Juniper EX4300-48T switches. You would create a device type with a model name "EX4300-48T" and assign it to the manufacturer "Juniper." You might then also create the following templates for it:

* One template for a console port ("Console")
* Two templates for power ports ("PSU0" and "PSU1")
* 48 templates for 1GE interfaces ("ge-0/0/0" through "ge-0/0/47")
* Four templates for 10GE interfaces ("xe-0/2/0" through "xe-0/2/3")

Once you've done this, every new device that you create as an instance of this type will automatically be assigned each of the components listed above.

Note that assignment of components from templates occurs only at the time of device creation: If you modify the templates of a device type, it will not affect devices which have already been created. However, you always have the option of adding, modifying, or deleting components of existing devices individually.

---

# Circuits

Circuits are communication links which connect two endpoints, typically over long distances. For example, a circuit might connect an enterprise to its Internet service provider. NetBox can track circuits and their providers.

### Providers

A provider is any entity which provides some form of connectivity. This obviously includes carriers which offer Internet and private transit service. However, it might also include Internet exchange (IX) points and even organizations with whom you peer directly.

Each provider may be assigned an autonomous system number (ASN) for reference. Each provider can also be assigned account and contact information, as well as miscellaneous comments.

### Circuits

A circuit represents a single physical data link connecting two endpoints. Each circuit belongs to a provider and must be assigned circuit ID which is unique to that provider. Each circuit must also be assigned to a site, and may optionally be connected to a specific interface on a specific device within that site.

NetBox also tracks miscellaneous circuit attributes (most of which are optional), including:

* Date of installation
* Port speed
* Commit rate
* Cross-connect ID
* Patch panel information

### Circuit Type

Circuits can be classified by type. For example:

* Internet transit
* Out-of-band connectivity
* Peering
* Private backhaul

Each circuit must be assigned exactly one circuit type.

---

# IPAM

IP address management (IPAM) entails the allocation of IP networks and addresses. Within NetBox, at least, IPAM also includes the management of VLAN assignments.

### VRF

A VRF object in NetBox represents a virtual routing and forwarding (VRF) domain within a network. Each VRF is essentially a separate routing table: the same IP prefix or address can exist in multiple VRFs. VRFs are commonly used to isolate customers or organizations from one another within a network.

Each VRF is assigned a name and a unique route distinguisher (RD). VRFs are an optional feature of NetBox: Any IP prefix or address not assigned to a VRF is said to belong to the "global" table.

### Aggregate

IPv4 address space is organized as a hierarchy, with more-specific (smaller) prefix arranged as child nodes under less-specific (larger) prefixes. For example:

* 10.0.0.0/8
    * 10.1.0.0/16
        * 10.1.2.0/24

The root of the IPv4 hierarchy is 0.0.0.0/0, which encompasses all possible IPv4 addresses (and similarly, ::/0 for IPv6). However, even the largest organizations use only a small fraction of the global address space. Therefore, it makes sense to track in NetBox only the address space which is of interest to your organization.

Aggregates serve as arbitrary top-level nodes in the IP space hierarchy. They allow you to easily construct your IP scheme without any clutter of unused address space. For instance, most organizations utilize some portion of the RFC 1918 private IPv4 space. So, you might define three aggregates for this space:

* 10.0.0.0/8
* 172.16.0.0/12
* 192.168.0.0/16

Additionally, you might define an aggregate for each large swath of public IPv4 space your organization uses. You'd also create aggregates for both globally routable and unique local IPv6 space.

Any prefixes you create in NetBox (discussed below) will be automatically organized under their respective aggregates. Any space within an aggregate which is not covered by an existing prefix will be annotated as available for allocation.

### RIRs

Regional Internet Registries (RIRs) are responsible for the allocation of global address space. The five RIRs are ARIN, RIPE, APNIC, LACNIC, and AFRINIC. However, some address space has been set aside for private or internal use only, such as defined in RFCs 1918 and 6598. NetBox considers these RFCs as a sort of RIR as well; that is, an authority which "owns" certain address space.

Each aggregate must be assigned to one RIR. NetBox by default will be populated with the RIRs listed above, however you are free to remove these and/or create your own if you choose.

### Prefixes

A prefix is an IPv4 or IPv6 network and mask expressed in CIDR notation (e.g. 192.0.2.0/24). A prefix entails only the "network portion" of an IP address; all bits in the address not covered by the mask must be zero.

Each prefix may be assigned to one VRF; prefixes not assigned to a VRF are assigned to the "global" table. Prefixes are also organized under their respective aggregates, irrespective of VRF assignment.

A prefix may optionally be assigned to one VLAN; a VLAN may have multiple prefixes assigned to it. This can be helpful is replicating real-world IP assignments. Each prefix may also be assigned a short description.

### Status

Each prefix is assigned an operational status. This may be one of the following:

* Container - A summary of child prefixes
* Active - Provisioned and in use
* Reserved - Earmarked for future use
* Deprecated - No longer in use

NetBox provides several statuses by default, but you are free to change them to suit the needs of your organization.

### Role

Whereas a status describes a prefix's operational state, a role describes its function. For example, roles might include:

* Access segment
* Infrastructure
* NAT
* Lab
* Out-of-band

Role assignment is optional. And like statuses, you are free to create your own.

### IP Addresses

An IP address comprises a single address (either IPv4 or IPv6) and its mask. Its mask should match exactly how the IP address is configured on an interface in the real world.

Like prefixes, an IP address can optionally be assigned to a VRF (or it will appear in the "global" table). IP addresses are automatically organized under parent prefixes within their respective VRFs. Each IP address can also be assigned a short description.

Each IP address can optionally be assigned to a device's interface; an interface may have multiple IP addresses assigned to it. Further, each device may have one of its interface IPs designated as its primary IP address.

One IP address can be designated as the network address translation (NAT) IP address for exactly one other IP address. This is useful primarily is denoting the public address for a private internal IP. Tracking one-to-many NAT (or PAT) assignments is not currently supported.

### VLAN

A VLAN represents an isolated layer two domain, identified by a name and a numeric ID (1-4094). Note that while it is good practice, neither VLAN names nor IDs must be unique within a site. This is to accommodate the fact that many real-world network use less-than-optimal VLAN allocations and may have overlapping VLAN ID assignments in practice.

Like prefixes, each VLAN is assigned an operational status and (optionally) a functional role.

---

# Secrets

"Secrets" are small amounts of data that must be kept confidential; for example, passwords and SNMP community strings. NetBox provides encrypted storage of secret data.

### Secret

A secret represents a single credential or other string which must be stored securely. Each secret is assigned to a device within NetBox. The plaintext value of a secret is encrypted to a ciphertext immediately prior to storage within the database using a 256-bit AES master key. A SHA256 hash of the plaintext is also stored along with each ciphertext to validate the decrypted plaintext.

Each secret can also store an optional name parameter, which is not encrypted. This may be useful for storing user names.

### Secret Roles

Each secret is assigned a functional role which indicates what it is used for. Typical roles might include:

* Login credentials
* SNMP community strings
* RADIUS/TACACS+ keys
* IKE key strings
* Routing protocol shared secrets

### User Keys

Each user within NetBox can associate his or her account with an RSA public key. If activated by an administrator, this user key will contain a unique, encrypted copy of the AES master key needed to retrieve secret data.

User keys may be created by users individually, however they are of no use until they have been activated by a user who already has access to retrieve secret data.
