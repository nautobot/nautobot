"""Custom choices for the vpn models."""

from nautobot.apps.choices import ChoiceSet


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
    group15 = "15"
    group16 = "16"
    group17 = "17"
    group18 = "18"
    group19 = "19"
    group20 = "20"
    group24 = "24"

    CHOICES = (
        (group1, "1"),
        (group2, "2"),
        (group5, "5"),
        (group14, "14"),
        (group15, "15"),
        (group16, "16"),
        (group17, "17"),
        (group18, "18"),
        (group19, "19"),
        (group20, "20"),
        (group24, "24"),
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


class PfsGroupChoices(ChoiceSet):
    """Choices for the pfs_group field on the VPNPhase2Policy model."""

    group1 = "1"
    group2 = "2"
    group5 = "5"
    group14 = "14"
    group19 = "19"
    group20 = "20"

    CHOICES = (
        (group1, "1"),
        (group2, "2"),
        (group5, "5"),
        (group14, "14"),
        (group19, "19"),
        (group20, "20"),
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
