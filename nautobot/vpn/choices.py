"""Custom choices for the vpn models."""

from nautobot.apps.choices import ChoiceSet


class VPNTunnelStatusChoices(ChoiceSet):
    STATUS_ACTIVE = "active"
    STATUS_DOWN = "down"
    STATUS_DEPRECATED = "deprecated"

    CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_DOWN, "Down"),
        (STATUS_DEPRECATED, "Deprecated"),
    )


class VPNTunnelEndpointRoleChoices(ChoiceSet):
    ROLE_PEER = "peer"
    ROLE_HUB = "hub"
    ROLE_SPOKE = "spoke"

    CHOICES = (
        (ROLE_PEER, "Peer"),
        (ROLE_HUB, "Hub"),
        (ROLE_SPOKE, "Spoke"),
    )


class IkeVersionChoices(ChoiceSet):
    """Choices for the ike_version field on the VPNPhase1Policy model."""

    ike_v1 = "IKEv1"
    ike_v2 = "IKEv2"

    CHOICES = (
        (ike_v1, "IKEv1"),
        (ike_v2, "IKEv2"),
    )


class EncryptionAlgorithmChoices(ChoiceSet):
    """Choices for the encryption_algorithm field on the VPNPhase1Policy model."""

    aes_128_cbc = "AES-128-CBC"
    aes_128_gcm = "AES-128-GCM"
    aes_192_cbc = "AES-192-CBC"
    aes_192_gcm = "AES-192-GCM"
    aes_256_cbc = "AES-256-CBC"
    aes_256_gcm = "AES-256-GCM"
    des = "DES"
    a3des = "3DES"

    CHOICES = (
        (aes_128_cbc, "AES-128-CBC"),
        (aes_128_gcm, "AES-128-GCM"),
        (aes_192_cbc, "AES-192-CBC"),
        (aes_192_gcm, "AES-192-GCM"),
        (aes_256_cbc, "AES-256-CBC"),
        (aes_256_gcm, "AES-256-GCM"),
        (des, "DES"),
        (a3des, "3DES"),
    )


class IntegrityAlgorithmChoices(ChoiceSet):
    """Choices for the integrity_algorithm field on the VPNPhase1Policy model."""

    md5 = "MD5"
    sha1 = "SHA1"
    sha256 = "SHA256"
    sha384 = "SHA384"
    sha512 = "SHA512"

    CHOICES = (
        (md5, "MD5"),
        (sha1, "SHA1"),
        (sha256, "SHA256"),
        (sha384, "SHA384"),
        (sha512, "SHA512"),
    )


class DhGroupChoices(ChoiceSet):
    """Choices for the dh_group field on the VPNPhase1Policy model."""

    group1 = "1"
    group2 = "2"
    group5 = "5"
    group14 = "14"
    group19 = "19"
    group20 = "20"
    group21 = "21"
    group22 = "22"
    group23 = "23"
    group24 = "24"
    group25 = "25"
    group26 = "26"
    group27 = "27"
    group28 = "28"
    group29 = "29"
    group30 = "30"
    group31 = "31"
    group32 = "32"
    group33 = "33"
    group34 = "34"

    CHOICES = (
        (group1, "Group 1"),
        (group2, "Group 2"),
        (group5, "Group 5"),
        (group14, "Group 14"),
        (group19, "Group 19"),
        (group20, "Group 20"),
        (group21, "Group 21"),
        (group22, "Group 22"),
        (group23, "Group 23"),
        (group24, "Group 24"),
        (group25, "Group 25"),
        (group26, "Group 26"),
        (group27, "Group 27"),
        (group28, "Group 28"),
        (group29, "Group 29"),
        (group30, "Group 30"),
        (group31, "Group 31"),
        (group32, "Group 32"),
        (group33, "Group 33"),
        (group34, "Group 34"),
    )


class AuthenticationMethodChoices(ChoiceSet):
    """Choices for the authentication_method field on the VPNPhase1Policy model."""

    psk = "PSK"
    rsa = "RSA"
    ecdsa = "ECDSA"
    certificate = "Certificate"

    CHOICES = (
        (psk, "PSK"),
        (rsa, "RSA"),
        (ecdsa, "ECDSA"),
        (certificate, "Certificate"),
    )


class EncapsulationChoices(ChoiceSet):
    """Choices for the encapsulation field on the VPNTunnel model."""

    ipsec_transport = "IPsec-Transport"
    ipsec_tunnel = "IPsec-Tunnel"
    ip_in_ip = "IP-in-IP"
    gre = "GRE"
    wireguard = "WireGuard"
    l2tp = "L2TP"
    pptp = "PPTP"
    openvpn = "OpenVPN"
    eoip = "EoIP"

    CHOICES = (
        (ipsec_transport, "IPsec-Transport"),
        (ipsec_tunnel, "IPsec-Tunnel"),
        (ip_in_ip, "IP-in-IP"),
        (gre, "GRE"),
        (wireguard, "WireGuard"),
        (l2tp, "L2TP"),
        (pptp, "PPTP"),
        (openvpn, "OpenVPN"),
        (eoip, "EoIP"),
    )
