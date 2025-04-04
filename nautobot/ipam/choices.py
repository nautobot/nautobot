from nautobot.core.choices import ChoiceSet


class IPAddressVersionChoices(ChoiceSet):
    VERSION_4 = 4
    VERSION_6 = 6

    CHOICES = (
        (VERSION_4, "IPv4"),
        (VERSION_6, "IPv6"),
    )


#
# Prefixes
#


class PrefixStatusChoices(ChoiceSet):
    STATUS_ACTIVE = "active"
    STATUS_RESERVED = "reserved"
    STATUS_DEPRECATED = "deprecated"

    CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_DEPRECATED, "Deprecated"),
    )


class PrefixTypeChoices(ChoiceSet):
    TYPE_CONTAINER = "container"
    TYPE_NETWORK = "network"
    TYPE_POOL = "pool"

    CHOICES = (
        (TYPE_CONTAINER, "Container"),
        (TYPE_NETWORK, "Network"),
        (TYPE_POOL, "Pool"),
    )


#
# IPAddresses
#


class IPAddressStatusChoices(ChoiceSet):
    STATUS_ACTIVE = "active"
    STATUS_RESERVED = "reserved"
    STATUS_DEPRECATED = "deprecated"

    CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_DEPRECATED, "Deprecated"),
    )


class IPAddressRoleChoices(ChoiceSet):
    ROLE_LOOPBACK = "loopback"
    ROLE_SECONDARY = "secondary"
    ROLE_ANYCAST = "anycast"
    ROLE_VIP = "vip"
    ROLE_VRRP = "vrrp"
    ROLE_HSRP = "hsrp"
    ROLE_GLBP = "glbp"
    ROLE_CARP = "carp"

    CHOICES = (
        (ROLE_LOOPBACK, "Loopback"),
        (ROLE_SECONDARY, "Secondary"),
        (ROLE_ANYCAST, "Anycast"),
        (ROLE_VIP, "VIP"),
        (ROLE_VRRP, "VRRP"),
        (ROLE_HSRP, "HSRP"),
        (ROLE_GLBP, "GLBP"),
        (ROLE_CARP, "CARP"),
    )

    CSS_CLASSES = {
        ROLE_LOOPBACK: "default",
        ROLE_SECONDARY: "primary",
        ROLE_ANYCAST: "warning",
        ROLE_VIP: "success",
        ROLE_VRRP: "success",
        ROLE_HSRP: "success",
        ROLE_GLBP: "success",
        ROLE_CARP: "success",
    }


class IPAddressTypeChoices(ChoiceSet):
    TYPE_DHCP = "dhcp"
    TYPE_HOST = "host"
    TYPE_SLAAC = "slaac"

    CHOICES = (
        (TYPE_DHCP, "DHCP"),
        (TYPE_HOST, "Host"),
        (TYPE_SLAAC, "SLAAC"),
    )


#
# VRFs
#


class VRFStatusChoices(ChoiceSet):
    STATUS_ACTIVE = "active"
    STATUS_DOWN = "down"
    STATUS_DEPRECATED = "deprecated"

    CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_DOWN, "Down"),
        (STATUS_DEPRECATED, "Deprecated"),
    )


#
# VLANs
#


class VLANStatusChoices(ChoiceSet):
    STATUS_ACTIVE = "active"
    STATUS_RESERVED = "reserved"
    STATUS_DEPRECATED = "deprecated"

    CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_DEPRECATED, "Deprecated"),
    )


#
# Services
#


class ServiceProtocolChoices(ChoiceSet):
    PROTOCOL_TCP = "tcp"
    PROTOCOL_UDP = "udp"

    CHOICES = (
        (PROTOCOL_TCP, "TCP"),
        (PROTOCOL_UDP, "UDP"),
    )
