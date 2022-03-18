import json

from nautobot.extras.jobs import Job, IPAddressVar, IPAddressWithMaskVar


name = "IP Addresses"


class TestIPAddresses(Job):
    class Meta:
        description = "Validate IP Addresses"

    ipv4_address = IPAddressVar(
        description="IPv4 Address",
    )
    ipv4_with_mask = IPAddressWithMaskVar(
        description="IPv4 with mask",
    )
    ipv4_network = IPAddressWithMaskVar(
        description="IPv4 network",
    )
    ipv6_address = IPAddressVar(
        description="IPv6 Address",
    )
    ipv6_with_mask = IPAddressWithMaskVar(
        description="IPv6 with mask",
    )
    ipv6_network = IPAddressWithMaskVar(
        description="IPv6 network",
    )

    def run(self, data, commit):
        ipv4_address = data["ipv4_address"]
        ipv4_with_mask = data["ipv4_with_mask"]
        ipv4_network = data["ipv4_network"]
        ipv6_address = data["ipv6_address"]
        ipv6_with_mask = data["ipv6_with_mask"]
        ipv6_network = data["ipv6_network"]

        # Log the data as JSON so we can pull it back out for testing.
        self.log_info(obj=json.dumps({k: str(v) for k, v in data.items()}), message="IP Address Test")

        self.log_warning(f"IPv4: {ipv4_address}")
        self.log_warning(f"IPv4: {ipv4_with_mask}")
        self.log_warning(f"IPv4: {ipv4_network}")
        self.log_warning(f"IPv6: {ipv6_address}")
        self.log_warning(f"IPv6: {ipv6_with_mask}")
        self.log_warning(f"IPv6: {ipv6_network}")

        self.log_success(message="Job didn't crash!")

        return "Nice IPs, bro."
