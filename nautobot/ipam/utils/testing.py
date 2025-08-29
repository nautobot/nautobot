"""Utilities for testing IPAM functionality, including data migrations."""

import random

from django.apps import apps
from netaddr import IPNetwork

from nautobot.ipam.models import get_default_namespace_pk

# Calculate the probabilities to use for the maybe_subdivide() function defined below.

# Frequency of IPv4 (leaf, network) Prefixes by each given mask length in a "realistic" data set.
# Based loosely on a survey of one large real-world deployment's IP space usage
FREQUENCY_BY_MASK_LENGTH = [
    0,  # /0
    0,
    0,
    0,
    0,  # /4
    0,
    0,
    0,
    0,  # /8
    0,
    0,
    0,
    0,  # /12
    1,
    2,
    4,
    16,  # /16
    8,
    12,
    16,
    20,  # /20
    120,
    150,
    400,
    5000,  # /24
    13000,
    16000,
    19000,
    17000,  # /28
    16000,
    32000,
    4000,
    1200,  # /32
]

# Amount of IP space needed at each mask length (frequency at this length, plus the rollup of subdivided nets)
#   Start calculation from the /32 frequency:
CUMULATIVE_BY_MASK_LENGTH = [FREQUENCY_BY_MASK_LENGTH[-1]]
#   Then work backwards to each parent mask length
for mask_len in range(len(FREQUENCY_BY_MASK_LENGTH) - 2, -1, -1):  # 31, ... 0
    CUMULATIVE_BY_MASK_LENGTH.append(CUMULATIVE_BY_MASK_LENGTH[-1] // 2 + FREQUENCY_BY_MASK_LENGTH[mask_len])
#   Reverse the list to get order by ascending prefix length, same as FREQUENCY_BY_MASK_LENGTH
CUMULATIVE_BY_MASK_LENGTH.reverse()

# Chance to stop subdividing at any given prefix length and create a network Prefix with this length
CHANCE_TO_STOP = [
    0 if not cumulative else frequency / cumulative
    for frequency, cumulative in zip(FREQUENCY_BY_MASK_LENGTH, CUMULATIVE_BY_MASK_LENGTH)
]


def maybe_subdivide(network):
    """
    Generator for recursively and probabilistically subdividing a network into subnets.

    Yields:
        IPNetwork: each constructed subdivision of the given network
    """
    if random.random() < CHANCE_TO_STOP[network.prefixlen]:  # noqa: S311  # suspicious-non-cryptographic-random-usage
        # Do not subdivide any further
        yield network
    else:
        # Split it into its two child networks and recurse
        subnets = network.subnet(network.prefixlen + 1)
        for subnet in subnets:
            yield from maybe_subdivide(subnet)


def maybe_random_instance(queryset, chance_of_none=0.75):
    """
    Helper function - randomly return either a random instance of the given queryset or None.
    """
    if random.random() < chance_of_none:  # noqa: S311  # suspicious-non-cryptographic-random-usage
        return None
    return random.choice(queryset)  # noqa: S311  # suspicious-non-cryptographic-random-usage


def create_prefixes_and_ips(initial_subnet: str, apps=apps, seed="Nautobot"):  # pylint: disable=redefined-outer-name
    """
    Create many (Nautobot 1.x) Prefix and IPAddress records under a given initial_subnet.

    The specific records created are pseudo-random (consistent for any given `initial_subnet` and `seed` values),
    but will *in general* consist of about 95% coverage of the subnet by non-overlapping Prefix partitions and about
    5% coverage of the subnet by individual IPAddress records. Additionally, about 10% of Prefixes and IPAddresses
    respectively will be duplicated one or more times.

    Args:
        initial_subnet (str): The parent subnet ("10.0.0.0/16") that will encompass the Prefix and IPAddress records.
        apps: Django application registry containing definitions of the (historical) Prefix, IPAddress, etc. models.
        seed: Random generator seed to ensure reproducible pseudo-random construction of the data.
    """
    IPAddress = apps.get_model("ipam", "IPAddress")
    Prefix = apps.get_model("ipam", "Prefix")
    Status = apps.get_model("extras", "Status")
    Tenant = apps.get_model("tenancy", "Tenant")
    VRF = apps.get_model("ipam", "VRF")

    print(f"Seeding the PRNG with seed {seed}")
    random.seed(seed)  # suspicious-non-cryptographic-random-usage

    if hasattr(Status, "slug"):
        status_active, _ = Status.objects.get_or_create(name="Active", defaults={"slug": "active"})
    else:
        status_active, _ = Status.objects.get_or_create(name="Active")

    for i in range(1, 11):
        Tenant.objects.get_or_create(name=f"{initial_subnet} Tenant {i}")
        if hasattr(VRF, "enforce_unique"):
            VRF.objects.get_or_create(
                name=f"{initial_subnet} VRF {i}",
                enforce_unique=False,  # TODO should some enforce_unique?
            )
        else:
            VRF.objects.get_or_create(name=f"{initial_subnet} VRF {i}")

    all_tenants = list(Tenant.objects.all())
    if hasattr(VRF, "namespace"):
        all_vrfs = list(VRF.objects.filter(namespace_id=get_default_namespace_pk()))
    else:
        all_vrfs = list(VRF.objects.all())

    create_prefixes(initial_subnet, all_tenants, all_vrfs, status_active, Prefix)
    create_ips(initial_subnet, all_tenants, all_vrfs, status_active, IPAddress)


def create_prefixes(initial_subnet, all_tenants, all_vrfs, status_active, Prefix):
    print(f"Creating Prefixes to subdivide {initial_subnet}")
    unique_prefix_count = 0
    duplicate_prefix_count = 0
    for subnet in maybe_subdivide(IPNetwork(initial_subnet)):
        if random.random() < 0.95:  # noqa: S311  # suspicious-non-cryptographic-random-usage
            # 95% chance to create any given Prefix
            vrf = maybe_random_instance(all_vrfs)
            if hasattr(Prefix, "vrf"):
                Prefix.objects.get_or_create(
                    network=str(subnet.network),
                    broadcast=str(subnet.broadcast if subnet.broadcast else subnet[-1]),
                    prefix_length=subnet.prefixlen,
                    status=status_active,
                    tenant=maybe_random_instance(all_tenants),
                    vrf=vrf,
                )
            else:
                prefix, _ = Prefix.objects.get_or_create(
                    network=str(subnet.network),
                    broadcast=str(subnet.broadcast if subnet.broadcast else subnet[-1]),
                    prefix_length=subnet.prefixlen,
                    ip_version=subnet.version,
                    status=status_active,
                    tenant=maybe_random_instance(all_tenants),
                )
                if vrf is not None:
                    vrf.prefixes.add(prefix)

            unique_prefix_count += 1
            if hasattr(Prefix, "vrf"):
                while random.random() < 0.1:  # noqa: S311  # suspicious-non-cryptographic-random-usage
                    # 10% repeating chance to create a duplicate(s) of this Prefix
                    Prefix.objects.create(
                        network=str(subnet.network),
                        broadcast=str(subnet.broadcast if subnet.broadcast else subnet[-1]),
                        prefix_length=subnet.prefixlen,
                        status=status_active,
                        tenant=maybe_random_instance(all_tenants),
                        vrf=maybe_random_instance(all_vrfs),
                    )
                    duplicate_prefix_count += 1
            else:
                # TODO: create prefixes in different namespaces?
                pass
    print(f"Created {unique_prefix_count} unique Prefixes and {duplicate_prefix_count} duplicates")


def create_ips(initial_subnet, all_tenants, all_vrfs, status_active, IPAddress):
    print(f"Creating IPAddresses within {initial_subnet}")
    unique_ip_count = 0
    duplicate_ip_count = 0
    for ip in IPNetwork(initial_subnet):
        if random.random() < 0.05:  # noqa: S311  # suspicious-non-cryptographic-random-usage
            # 5% chance to create any given IP address
            network = IPNetwork(ip)
            if hasattr(IPAddress, "prefix_length"):
                IPAddress.objects.create(
                    host=str(network.ip),
                    broadcast=str(network.broadcast if network.broadcast else network[-1]),
                    prefix_length=network.prefixlen,
                    status=status_active,
                    tenant=maybe_random_instance(all_tenants),
                    vrf=maybe_random_instance(all_vrfs),
                )
            else:
                IPAddress.objects.create(
                    host=str(network.ip),
                    mask_length=network.prefixlen,
                    ip_version=network.version,
                    status=status_active,
                    tenant=maybe_random_instance(all_tenants),
                )
            unique_ip_count += 1
            if hasattr(IPAddress, "prefix_length"):
                while random.random() < 0.1:  # noqa: S311  # suspicious-non-cryptographic-random-usage
                    # 10% repeating chance to create a duplicate(s) of this IP
                    IPAddress.objects.create(
                        host=str(network.ip),
                        broadcast=str(network.broadcast if network.broadcast else network[-1]),
                        prefix_length=network.prefixlen,
                        status=status_active,
                        tenant=maybe_random_instance(all_tenants),
                        vrf=maybe_random_instance(all_vrfs),
                    )
                    duplicate_ip_count += 1
            else:
                # TODO: create duplicate IPs in other namespaces?
                pass
    print(f"Created {unique_ip_count} unique IPAddresses and {duplicate_ip_count} duplicates")
