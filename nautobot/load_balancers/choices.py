"""Custom choices for the Load Balancer models."""

from nautobot.core.choices import ChoiceSet


class SourceNATTypeChoices(ChoiceSet):
    """Source NAT Type choices for VirtualServers."""

    TYPE_AUTO = "auto"
    TYPE_POOL = "pool"
    TYPE_STATIC = "static"

    CHOICES = (
        (TYPE_AUTO, "Auto"),
        (TYPE_POOL, "Pool"),
        (TYPE_STATIC, "Static"),
    )


class LoadBalancerTypeChoices(ChoiceSet):
    """Load balancer type choices for VirtualServers."""

    TYPE_LAYER2 = "layer2"
    TYPE_LAYER4 = "layer4"
    TYPE_LAYER7 = "layer7"
    TYPE_DNS = "dns"

    CHOICES = (
        (TYPE_LAYER2, "Layer 2"),
        (TYPE_LAYER4, "Layer 4"),
        (TYPE_LAYER7, "Layer 7"),
        (TYPE_DNS, "DNS"),
    )


class ProtocolChoices(ChoiceSet):
    """Protocol choices for VirtualServers."""

    # Layer4
    PROTOCOL_TCP = "tcp"
    PROTOCOL_UDP = "udp"
    PROTOCOL_ICMP = "icmp"
    PROTOCOL_SCTP = "sctp"

    # Layer7
    PROTOCOL_HTTP = "http"
    PROTOCOL_HTTPS = "https"
    PROTOCOL_HTTP2 = "http2"
    PROTOCOL_GRPC = "grpc"
    PROTOCOL_QUIC = "quic"

    # DNS
    PROTOCOL_DNS = "dns"

    # Any
    PROTOCOL_ANY = "any"

    CHOICES = (
        (
            "Layer 4",
            (
                (PROTOCOL_TCP, "TCP"),
                (PROTOCOL_UDP, "UDP"),
                (PROTOCOL_ICMP, "ICMP"),
                (PROTOCOL_SCTP, "SCTP"),
            ),
        ),
        (
            "Layer 7",
            (
                (PROTOCOL_HTTP, "HTTP"),
                (PROTOCOL_HTTPS, "HTTPS"),
                (PROTOCOL_HTTP2, "HTTP2"),
                (PROTOCOL_GRPC, "gRPC"),
                (PROTOCOL_QUIC, "QUIC"),
            ),
        ),
        ("DNS", ((PROTOCOL_DNS, "DNS"),)),
        ("Any", ((PROTOCOL_ANY, "Any"),)),
    )


class LoadBalancingAlgorithmChoices(ChoiceSet):
    """Choices for the load_balancing_algorithm field on the LoadBalancerPool model."""

    # TODO Pull from Netutils
    ROUND_ROBIN = "round_robin"
    URL_HASH = "url_hash"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    LEAST_BANDWIDTH = "least_bandwidth"
    LEAST_PACKETS = "least_packets"
    DOMAIN_HASH = "domain_hash"
    DESTINATION_IP_HASH = "destination_ip_hash"
    SOURCE_IP_HASH = "source_ip_hash"
    SRCIP_DESTIP_HASH = "srcip_destip_hash"
    LEAST_REQUEST = "least_request"
    CUSTOM_LOAD = "custom_load"
    SRCIP_SRCPORT_HASH = "srcip_srcport_hash"

    CHOICES = (
        (ROUND_ROBIN, "Round Robin"),
        (URL_HASH, "URL Hash"),
        (LEAST_CONNECTIONS, "Least Connections"),
        (LEAST_RESPONSE_TIME, "Least Response Time"),
        (LEAST_BANDWIDTH, "Least Bandwidth"),
        (LEAST_PACKETS, "Least Packets"),
        (DOMAIN_HASH, "Domain Hash"),
        (DESTINATION_IP_HASH, "Destination IP Hash"),
        (SOURCE_IP_HASH, "Source IP Hash"),
        (SRCIP_DESTIP_HASH, "Source IP Destination IP Hash"),
        (LEAST_REQUEST, "Least Request"),
        (CUSTOM_LOAD, "Custom Load"),
        (SRCIP_SRCPORT_HASH, "Source IP Source Port Hash"),
    )


class LoadBalancerPoolMemberStatusChoices(ChoiceSet):
    """Choices for the status field on the LoadBalancerPoolMember model."""

    STATUS_ACTIVE = "active"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_PLANNED = "planned"
    STATUS_FAILED = "failed"
    STATUS_DECOMMISSIONING = "decommissioning"

    CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_MAINTENANCE, "Maintenance"),
        (STATUS_PLANNED, "Planned"),
        (STATUS_FAILED, "Failed"),
        (STATUS_DECOMMISSIONING, "Decommissioning"),
    )


class HealthCheckTypeChoices(ChoiceSet):
    """Choices for the health_check_type field on the HealthCheckMonitor model."""

    PING = "ping"
    TCP = "tcp"
    DNS = "dns"
    HTTP = "http"
    HTTPS = "https"
    CUSTOM = "custom"

    CHOICES = (
        (PING, "Ping"),
        (TCP, "TCP"),
        (DNS, "DNS"),
        (HTTP, "HTTP"),
        (HTTPS, "HTTPS"),
        (CUSTOM, "Custom"),
    )


class CertificateTypeChoices(ChoiceSet):
    """Choices for the certificate_type field on the CertificateProfile model."""

    TYPE_CLIENT = "client"
    TYPE_SERVER = "server"
    TYPE_MTLS = "mutual_tls"

    CHOICES = (
        (TYPE_CLIENT, "Client"),
        (TYPE_SERVER, "Server"),
        (TYPE_MTLS, "mTLS (Mutual TLS)"),
    )
