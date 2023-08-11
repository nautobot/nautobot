import netaddr

from nautobot.dcim.models import Interface
from nautobot.extras.models import RelationshipAssociation
from nautobot.ipam.constants import VLAN_VID_MAX, VLAN_VID_MIN
from nautobot.ipam.models import Prefix, VLAN
from nautobot.ipam.querysets import IPAddressQuerySet
from nautobot.virtualization.models import VMInterface


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
                f"{first_ip_in_prefix}/{prefix.prefixlen}",
            )
        ]

    # sort the IP address list
    if isinstance(ipaddress_list, IPAddressQuerySet):
        ipaddress_list = ipaddress_list.order_by("host")
    elif isinstance(ipaddress_list, list):
        ipaddress_list.sort(key=lambda ip: ip.host)

    # Account for any available IPs before the first real IP
    if ipaddress_list[0].address.ip > first_ip_in_prefix:
        skipped_count = int(ipaddress_list[0].address.ip - first_ip_in_prefix)
        first_skipped = f"{first_ip_in_prefix}/{prefix.prefixlen}"
        output.append((skipped_count, first_skipped))

    # Iterate through existing IPs and annotate free ranges
    for ip in ipaddress_list:
        if prev_ip:
            diff = int(ip.address.ip - prev_ip.address.ip)
            if diff > 1:
                first_skipped = f"{prev_ip.address.ip + 1}/{prefix.prefixlen}"
                output.append((diff - 1, first_skipped))
        output.append(ip)
        prev_ip = ip

    # Include any remaining available IPs
    if prev_ip.address.ip < last_ip_in_prefix:
        skipped_count = int(last_ip_in_prefix - prev_ip.address.ip)
        first_skipped = f"{prev_ip.address.ip + 1}/{prefix.prefixlen}"
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


def handle_relationship_changes_when_merging_ips(merged_ip, merged_attributes, collapsed_ips):
    """
    Update/Delete RelationshipAssociation instances after we collapsed the IPs.
    """
    for side, relationships in merged_ip.get_relationships_data().items():
        for relationship, value in relationships.items():
            # could be a pk or a list of pks
            # When it is a list of pks, the opposite side of ip has_many=True and the list of pks returned are relationship association pks
            # When it is a single pk, it is the opposite side id of the relationship association
            new_rel_values = merged_attributes.get("cr_" + relationship.key)
            if new_rel_values:
                if side == "source":
                    # handle when `IPAddress`` is on the source side and the opposite side has many objects.
                    if value.get("has_many"):
                        pk_list = new_rel_values.split(",")
                        # no-op if RelationshipAssociations already exist
                        if set(
                            RelationshipAssociation.objects.filter(relationship=relationship, source_id=merged_ip.pk)
                        ) == set(RelationshipAssociation.objects.filter(pk__in=pk_list)):
                            continue
                        RelationshipAssociation.objects.filter(
                            relationship=relationship,
                            source_id=merged_ip.pk,
                        ).delete()
                        updated_associations = RelationshipAssociation.objects.filter(pk__in=pk_list)
                        updated_associations.update(source_id=merged_ip.pk)
                    # handle when `IPAddress`` is on the source side and the opposite side has a single object.
                    else:
                        RelationshipAssociation.objects.filter(
                            relationship=relationship,
                            destination_id=new_rel_values,
                        ).delete()
                        RelationshipAssociation.objects.filter(
                            relationship=relationship, source_id=merged_ip.pk
                        ).delete()
                        new_rel = RelationshipAssociation(
                            relationship=relationship,
                            source_type=relationship.source_type,
                            source_id=merged_ip.pk,
                            destination_type=relationship.destination_type,
                            destination_id=new_rel_values,
                        )
                        new_rel.validated_save()
                elif side == "destination":
                    # handle when `IPAddress`` is on the destination side and the opposite side has many objects.
                    if value.get("has_many"):
                        pk_list = new_rel_values.split(",")
                        # no-op if RelationshipAssociations already exist
                        if set(
                            RelationshipAssociation.objects.filter(
                                relationship=relationship, destination_id=merged_ip.pk
                            )
                        ) == set(RelationshipAssociation.objects.filter(pk__in=pk_list)):
                            continue
                        RelationshipAssociation.objects.filter(
                            relationship=relationship,
                            destination_id=merged_ip.pk,
                        ).delete()
                        updated_associations.update(destination_id=merged_ip.pk)
                    # handle when `IPAddress`` is on the destination side and the opposite side has a single object.
                    else:
                        RelationshipAssociation.objects.filter(
                            relationship=relationship,
                            source_id=new_rel_values,
                        ).delete()
                        RelationshipAssociation.objects.filter(
                            relationship=relationship, destination_id=merged_ip.pk
                        ).delete()
                        new_rel = RelationshipAssociation(
                            relationship=relationship,
                            source_type=relationship.source_type,
                            source_id=new_rel_values,
                            destination_type=relationship.destination_type,
                            destination_id=merged_ip.pk,
                        )
                        new_rel.validated_save()
                else:
                    # Peer side is very tricky
                    # We delete all RelationshipAssociations with merged_ip on either side
                    # and save them destination_id and source_id in a dictionary lookup
                    # to avoid redundant RelationshipAssociations
                    lookup = {}
                    peer_source_associations = RelationshipAssociation.objects.filter(
                        relationship=relationship, destination_id=merged_ip.pk
                    )
                    for association in peer_source_associations:
                        lookup[str(association.pk)] = association.source_id
                    peer_source_associations.delete()
                    peer_destination_associations = RelationshipAssociation.objects.filter(
                        relationship=relationship, source_id=merged_ip.pk
                    )
                    for association in peer_destination_associations:
                        lookup[str(association.pk)] = association.destination_id
                    peer_destination_associations.delete()
                    if value.get("has_many"):
                        pk_list = new_rel_values.split(",")
                        for pk in pk_list:
                            # rebuild the RelationshipAssociation if it is deleted.
                            if pk in lookup:
                                new_rel = RelationshipAssociation(
                                    relationship=relationship,
                                    source_type=relationship.source_type,
                                    source_id=merged_ip.pk,
                                    destination_type=relationship.destination_type,
                                    destination_id=lookup.get(pk),
                                )
                                new_rel.validated_save()
                            else:
                                # update the RelationshipAssociation if it still exists.
                                rel = RelationshipAssociation.objects.get(pk=pk)
                                if rel.source in collapsed_ips and rel.destination in collapsed_ips:
                                    continue
                                if rel.source in collapsed_ips:
                                    rel.source_id = merged_ip.pk
                                else:
                                    rel.destination_id = merged_ip.pk
                                rel.validated_save()
                    else:
                        # handle peer one to one relationship
                        pk = new_rel_values
                        # If the relationship is peer one to one then, only one of the below statements will execute
                        # and the other one should be a no-op and only one RelationshipAssociation will be deleted.
                        RelationshipAssociation.objects.filter(relationship=relationship, destination_id=pk).delete()
                        RelationshipAssociation.objects.filter(relationship=relationship, source_id=pk).delete()
                        new_rel = RelationshipAssociation(
                            relationship=relationship,
                            source_type=relationship.source_type,
                            source_id=merged_ip.pk,
                            destination_type=relationship.destination_type,
                            destination_id=pk,
                        )
                        new_rel.validated_save()
            else:
                # if new_rel_values returned here are empty, that means the user decided to discard any RelationshipAssociations of that Relationship.
                # we make sure that we delete any relationship associations that are related to the surviving IP
                # The rest of the associations will be automatically deleted when we delete the collapsed IPs.
                if side == "source":
                    RelationshipAssociation.objects.filter(relationship=relationship, source_id=merged_ip.pk).delete()
                elif side == "destination":
                    RelationshipAssociation.objects.filter(
                        relationship=relationship, destination_id=merged_ip.pk
                    ).delete()
                else:
                    RelationshipAssociation.objects.filter(relationship=relationship, source_id=merged_ip.pk).delete()
                    RelationshipAssociation.objects.filter(
                        relationship=relationship, destination_id=merged_ip.pk
                    ).delete()


def retrieve_interface_or_vminterface_from_request(request):
    """
    Retrieve either an Interface or VMInterface based on the provided request's GET parameters.

    Parameters:
        - request (HttpRequest): The HTTP request object.

    Returns:
        tuple:
            - Interface/VMInterface or None: The found interface object, or None if not found.
            - str or None: An error message if the interface is not found, otherwise None.
    """
    interface_model = Interface if "interface" in request.GET else VMInterface
    interface_id = request.GET.get("interface") or request.GET.get("vminterface")
    try:
        obj = interface_model.objects.restrict(request.user, "change").get(id=interface_id)
        return obj, None
    except interface_model.DoesNotExist:
        return None, f'{interface_model.__name__} with id "{interface_id}" not found.'
