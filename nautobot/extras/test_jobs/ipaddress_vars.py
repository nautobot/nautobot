import json

from nautobot.extras.jobs import get_task_logger

from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, IPAddressVar, IPAddressWithMaskVar


logger = get_task_logger(__name__)
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

    def run(self, ipv4_address, ipv4_with_mask, ipv4_network, ipv6_address, ipv6_with_mask, ipv6_network):
        # Log the data as JSON so we can pull it back out for testing.
        logger.info(
            "IP Address Test",
            extra={
                "object": json.dumps(
                    {
                        "ipv4_address": str(ipv4_address),
                        "ipv4_with_mask": str(ipv4_with_mask),
                        "ipv4_network": str(ipv4_network),
                        "ipv6_address": str(ipv6_address),
                        "ipv6_with_mask": str(ipv6_with_mask),
                        "ipv6_network": str(ipv6_network),
                    }
                ),
            },
        )

        logger.warning("IPv4: %s", ipv4_address)
        logger.warning("IPv4: %s", ipv4_with_mask)
        logger.warning("IPv4: %s", ipv4_network)
        logger.warning("IPv6: %s", ipv6_address)
        logger.warning("IPv6: %s", ipv6_with_mask)
        logger.warning("IPv6: %s", ipv6_network)

        logger.info("Job didn't crash!")

        return "Nice IPs, bro."


register_jobs(TestIPAddresses)
