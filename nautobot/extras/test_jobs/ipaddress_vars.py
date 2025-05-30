import json

import netaddr

from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import get_task_logger, IPAddressVar, IPAddressWithMaskVar, Job

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

    def before_start(self, task_id, args, kwargs):
        for expected_kwarg in self._get_vars().keys():
            if expected_kwarg not in kwargs:
                raise RuntimeError(f"kwargs should contain {expected_kwarg} but it doesn't!")
            if kwargs[expected_kwarg] is None:
                raise RuntimeError(f"kwargs[{expected_kwarg}] is unexpectedly None!")

    def run(  # pylint:disable=arguments-differ
        self, *, ipv4_address, ipv4_with_mask, ipv4_network, ipv6_address, ipv6_with_mask, ipv6_network
    ):
        if not isinstance(ipv4_address, netaddr.IPAddress):
            raise RuntimeError(f"Expected ipv4_address to be a netaddr.IPAddress, but it was {ipv4_address!r}")
        if not isinstance(ipv4_with_mask, netaddr.IPNetwork):
            raise RuntimeError(f"Expected ipv4_with_mask to be a netaddr.IPNetwork, but it was {ipv4_with_mask!r}")
        if not isinstance(ipv4_network, netaddr.IPNetwork):
            raise RuntimeError(f"Expected ipv4_network to be a netaddr.IPNetwork, but it was {ipv4_network!r}")
        if not isinstance(ipv6_address, netaddr.IPAddress):
            raise RuntimeError(f"Expected ipv6_address to be a netaddr.IPAddress, but it was {ipv6_address!r}")
        if not isinstance(ipv6_with_mask, netaddr.IPNetwork):
            raise RuntimeError(f"Expected ipv6_with_mask to be a netaddr.IPNetwork, but it was {ipv6_with_mask!r}")
        if not isinstance(ipv6_network, netaddr.IPNetwork):
            raise RuntimeError(f"Expected ipv6_network to be a netaddr.IPNetwork, but it was {ipv6_network!r}")
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

    def on_success(self, retval, task_id, args, kwargs):
        if retval != "Nice IPs, bro.":
            raise RuntimeError(f"retval is unexpected: {retval!r}")
        for expected_kwarg in self._get_vars().keys():
            if expected_kwarg not in kwargs:
                raise RuntimeError(f"kwargs should contain {expected_kwarg} but it doesn't!")
            if kwargs[expected_kwarg] is None:
                raise RuntimeError(f"kwargs[{expected_kwarg}] is unexpectedly None!")

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if retval != "Nice IPs, bro.":
            raise RuntimeError(f"retval is unexpected: {retval!r}")
        for expected_kwarg in self._get_vars().keys():
            if expected_kwarg not in kwargs:
                raise RuntimeError(f"kwargs should contain {expected_kwarg} but it doesn't!")
            if kwargs[expected_kwarg] is None:
                raise RuntimeError(f"kwargs[{expected_kwarg}] is unexpectedly None!")


register_jobs(TestIPAddresses)
