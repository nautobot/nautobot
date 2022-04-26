import netaddr

from .constants import VLAN_VID_MAX, VLAN_VID_MIN
from .models import Prefix, VLAN


def add_available_prefixes(parent, prefix_list):
    """
    Create fake Prefix objects for all unallocated space within a prefix.
    """

    # Find all unallocated space
    available_prefixes = netaddr.IPSet(parent) ^ netaddr.IPSet([p.prefix for p in prefix_list])
    available_prefixes = [Prefix(prefix=p, status=None) for p in available_prefixes.iter_cidrs()]

    # Concatenate and sort complete list of children
    prefix_list = list(prefix_list) + available_prefixes
    prefix_list.sort(key=lambda p: p.prefix)

    return prefix_list


def add_available_ipaddresses(prefix, ipaddress_list, is_pool=False):
    """
    Annotate ranges of available IP addresses within a given prefix. If is_pool is True, the first and last IP will be
    considered usable (regardless of mask length).
    """

    output = []
    prev_ip = None

    # Ignore the network and broadcast addresses for non-pool IPv4 prefixes larger than /31.
    if prefix.version == 4 and prefix.prefixlen < 31 and not is_pool:
        first_ip_in_prefix = netaddr.IPAddress(prefix.first + 1)
        last_ip_in_prefix = netaddr.IPAddress(prefix.last - 1)
    else:
        first_ip_in_prefix = netaddr.IPAddress(prefix.first)
        last_ip_in_prefix = netaddr.IPAddress(prefix.last)

    if not ipaddress_list:
        return [
            (
                int(last_ip_in_prefix - first_ip_in_prefix + 1),
                "{}/{}".format(first_ip_in_prefix, prefix.prefixlen),
            )
        ]

    # Account for any available IPs before the first real IP
    if ipaddress_list[0].address.ip > first_ip_in_prefix:
        skipped_count = int(ipaddress_list[0].address.ip - first_ip_in_prefix)
        first_skipped = "{}/{}".format(first_ip_in_prefix, prefix.prefixlen)
        output.append((skipped_count, first_skipped))

    # Iterate through existing IPs and annotate free ranges
    for ip in ipaddress_list:
        if prev_ip:
            diff = int(ip.address.ip - prev_ip.address.ip)
            if diff > 1:
                first_skipped = "{}/{}".format(prev_ip.address.ip + 1, prefix.prefixlen)
                output.append((diff - 1, first_skipped))
        output.append(ip)
        prev_ip = ip

    # Include any remaining available IPs
    if prev_ip.address.ip < last_ip_in_prefix:
        skipped_count = int(last_ip_in_prefix - prev_ip.address.ip)
        first_skipped = "{}/{}".format(prev_ip.address.ip + 1, prefix.prefixlen)
        output.append((skipped_count, first_skipped))

    return output


def add_available_vlans(vlan_group, vlans):
    """
    Create fake records for all gaps between used VLANs
    """
    if not vlans:
        return [{"vid": VLAN_VID_MIN, "available": VLAN_VID_MAX - VLAN_VID_MIN + 1}]

    prev_vid = VLAN_VID_MAX
    new_vlans = []
    for vlan in vlans:
        if vlan.vid - prev_vid > 1:
            new_vlans.append({"vid": prev_vid + 1, "available": vlan.vid - prev_vid - 1})
        prev_vid = vlan.vid

    if vlans[0].vid > VLAN_VID_MIN:
        new_vlans.append({"vid": VLAN_VID_MIN, "available": vlans[0].vid - VLAN_VID_MIN})
    if prev_vid < VLAN_VID_MAX:
        new_vlans.append({"vid": prev_vid + 1, "available": VLAN_VID_MAX - prev_vid})

    vlans = list(vlans) + new_vlans
    vlans.sort(key=lambda v: v.vid if isinstance(v, VLAN) else v["vid"])

    return vlans
