import collections
import sys

from django.core.exceptions import ValidationError
from django.db import models
import netaddr


BASE_NAME = "Cleanup Namespace"
DESCRIPTION = "Created by Nautobot 2.0 IPAM data migrations."
GLOBAL_NS = "Global"


def process_namespaces(apps, schema_editor):
    print("\n", end="")

    # Fail if any interface or vm interface has IPs with different VRFs
    check_interface_vrfs(apps)

    # Prefix Broadcast is a derived field, so we should update it before we start
    ensure_correct_prefix_broadcast(apps)

    # Cleanup Prefixes and IPAddresses version fields
    add_prefix_and_ip_address_version(apps)

    # VRFs
    process_vrfs(apps)

    # IPAddresses
    process_ip_addresses(apps)

    # Prefixes
    process_prefix_duplicates(apps)
    reparent_prefixes(apps)

    # Make another pass across all VRFs to duplicate it if it has prefixes
    # in another namespace (non-unique VRFs with duplicate Prefixes)
    copy_vrfs_to_cleanup_namespaces(apps)

    # [VM]Interfaces
    process_interfaces(apps)

    # VRF-Prefix M2M
    process_vrfs_prefixes_m2m(apps)


def check_interface_vrfs(apps):
    """
    Enumerate all Interface and VMInterface objects and raise an exception if any interface is found that is associated
    to more than one distinct VRF through the ip_address many-to-many relationship.

    Args:
        apps: Django apps module

    Returns:
        None
    """

    Interface = apps.get_model("dcim", "Interface")
    VMInterface = apps.get_model("virtualization", "VMInterface")

    interfaces_with_multiple_vrfs = (
        Interface.objects.annotate(vrf_count=models.Count("ip_addresses__vrf", distinct=True))
        .filter(vrf_count__gt=1)
        .distinct()
    )
    interfaces_with_mixed_vrfs = (
        Interface.objects.filter(ip_addresses__vrf__isnull=True).filter(ip_addresses__vrf__isnull=False).distinct()
    )
    vm_interfaces_with_multiple_vrfs = (
        VMInterface.objects.annotate(vrf_count=models.Count("ip_addresses__vrf", distinct=True))
        .filter(vrf_count__gt=1)
        .distinct()
    )
    vm_interfaces_with_mixed_vrfs = (
        VMInterface.objects.filter(ip_addresses__vrf__isnull=True).filter(ip_addresses__vrf__isnull=False).distinct()
    )

    if any(
        [
            interfaces_with_multiple_vrfs.exists(),
            interfaces_with_mixed_vrfs.exists(),
            vm_interfaces_with_multiple_vrfs.exists(),
            vm_interfaces_with_mixed_vrfs.exists(),
        ]
    ):
        raise ValidationError(
            "You cannot migrate Interfaces or VMInterfaces that have IPs with differing VRFs:\n"
            f"{list(interfaces_with_multiple_vrfs)}\n"
            f"{list(interfaces_with_mixed_vrfs)}\n"
            f"{list(vm_interfaces_with_multiple_vrfs)}\n"
            f"{list(vm_interfaces_with_mixed_vrfs)}"
        )


def process_vrfs(apps):
    """
    Enumerate all VRF objects in the database and attempt to find suitable Namespace with no duplicate VRF names and
    no duplicate Prefixes associated to the VRF. Any VRF with `enforce_unique` set and has related prefixes will be
    moved to its own Namespace. All other VRFs will be checked for duplicate names and Prefixes and moved to a cleanup
    Namespace if any duplicates are found.

    Args:
        apps: Django apps module

    Returns:
        None
    """
    VRF = apps.get_model("ipam", "VRF")
    vrfs = VRF.objects.all().order_by("name", "rd")
    unique_non_empty_vrfs = vrfs.filter(enforce_unique=True).exclude(ip_addresses__isnull=True, prefixes__isnull=True)
    # At the point in the migration where we iterate through vrfs in global_ns_vrfs, every vrf that
    # has already been processed has been moved to a new namespace. Anything left in the global
    # namespace has yet to be processed which is why we're iterating through this on the second
    # loop.
    global_ns_vrfs = vrfs.filter(namespace__name=GLOBAL_NS)

    # Case 0: VRFs with enforce_unique move to their own Namespace.
    for vrf in unique_non_empty_vrfs:
        if "test" not in sys.argv:
            print(f">>> Processing migration for VRF {vrf.name!r}, Namespace {vrf.namespace.name!r}")
        vrf.namespace = create_vrf_namespace(apps, vrf)
        vrf.save()
        vrf.prefixes.update(namespace=vrf.namespace)
        if "test" not in sys.argv:
            print(f"    VRF {vrf.name!r} migrated to Namespace {vrf.namespace.name!r}")

    # Case 00: VRFs with duplicate names or prefixes move to a Cleanup Namespace.
    # Case 1 is not included here because it is a no-op.
    for vrf in global_ns_vrfs.annotate(prefix_count=models.Count("prefixes")).order_by("-prefix_count"):
        if "test" not in sys.argv:
            print(f">>> Processing migration for VRF {vrf.name!r}, Namespace {vrf.namespace.name!r}")
        original_namespace = vrf.namespace
        vrf.namespace = get_next_vrf_cleanup_namespace(apps, vrf)
        vrf.save()
        if vrf.namespace != original_namespace:
            vrf.prefixes.update(namespace=vrf.namespace)
            print(f"    VRF {vrf.name!r} migrated from Namespace {original_namespace.name!r} to {vrf.namespace.name!r}")


def add_prefix_and_ip_address_version(apps):
    """
    Enumerate all Prefix and IPAddress objects in the database and populate the ip_version field.

    Args:
        apps: Django apps module

    Returns:
        None
    """
    Prefix = apps.get_model("ipam", "Prefix")
    IPAddress = apps.get_model("ipam", "IPAddress")

    if "test" not in sys.argv:
        print(">>> Populating Prefix.ip_version field")
    for pfx in Prefix.objects.all():
        cidr = validate_cidr(apps, pfx)
        pfx.ip_version = cidr.version
        pfx.save()

    if "test" not in sys.argv:
        print(">>> Populating IPAddress.ip_version field")
    for ip in IPAddress.objects.all():
        cidr = validate_cidr(apps, ip)
        ip.ip_version = cidr.version
        ip.save()


def process_ip_addresses(apps):
    """
    Enumerate collected IPs and parent them.

    - For IPs with found parents: Set that parent and save the `IPAddress`.
    - For orphaned IPs (missing parents):
        - Generate a network from the `IPAddress`
        - Get or create the parent `Prefix`
        - Set that as the parent and save the `IPAddress`

    Args:
        apps: Django apps module

    Returns:
        None
    """
    # Find the correct namespace for each IPAddress and move it if necessary.
    IPAddress = apps.get_model("ipam", "IPAddress")
    Namespace = apps.get_model("ipam", "Namespace")
    Prefix = apps.get_model("ipam", "Prefix")

    # Explicitly set the parent for those that were found and save them.
    for ip in IPAddress.objects.filter(parent__isnull=True).order_by("-vrf", "-tenant"):
        potential_parents = get_closest_parent(apps, ip, Prefix.objects.all())
        for prefix in potential_parents:
            if not prefix.ip_addresses.filter(host=ip.host).exists():
                ip.parent = prefix
                ip.save()
                break

    # For IPs with no discovered parent, create one and assign it to the IP.
    global_ns = Namespace.objects.get(name=GLOBAL_NS)
    for orphaned_ip in IPAddress.objects.filter(parent__isnull=True):
        ip_repr = str(validate_cidr(apps, orphaned_ip))
        if "test" not in sys.argv:
            print(f">>> Processing Parent migration for orphaned IPAddress {ip_repr!r}")

        new_parent_cidr = generate_parent_prefix(apps, orphaned_ip)
        network = new_parent_cidr.network
        prefix_length = new_parent_cidr.prefixlen
        potential_parents = Prefix.objects.filter(network=network, prefix_length=prefix_length).exclude(
            ip_addresses__host=orphaned_ip.host
        )
        if potential_parents.exists():
            new_parent = potential_parents.first()

        else:
            broadcast = new_parent_cidr[-1]
            # This can result in duplicate Prefixes being created in the global_ns but that will be
            # cleaned up subsequently in `process_prefix_duplicates`.
            new_parent = Prefix.objects.create(
                ip_version=orphaned_ip.ip_version,
                network=network,
                broadcast=broadcast,
                tenant=orphaned_ip.tenant,
                vrf=orphaned_ip.vrf,
                prefix_length=prefix_length,
                namespace=orphaned_ip.vrf.namespace if orphaned_ip.vrf else global_ns,
                description=DESCRIPTION,
            )
        orphaned_ip.parent = new_parent
        orphaned_ip.save()

        parent_repr = str(validate_cidr(apps, new_parent))
        if "test" not in sys.argv:
            print(
                f"    IPAddress {ip_repr!r} migrated to Parent Prefix {parent_repr!r} in Namespace {new_parent.namespace.name!r}"
            )

    # By this point we should arrive at NO orphaned IPAddress objects.
    if IPAddress.objects.filter(parent__isnull=True).exists():
        raise SystemExit("Unexpected orphaned IPAddress objects found.")


def process_prefix_duplicates(apps):
    """
    Enumerate all Prefix objects in the database and attempt to find suitable Namespace with no Prefixes with duplicate
    network and prefix length. Duplicate prefixes will be moved to a cleanup Namespace if any duplicates are found.

    Args:
        apps: Django apps module

    Returns:
        None
    """
    Namespace = apps.get_model("ipam", "Namespace")
    Prefix = apps.get_model("ipam", "Prefix")
    global_namespace = Namespace.objects.get(name=GLOBAL_NS)

    namespaces = list(Namespace.objects.all())
    # Always start with the Global Namespace.
    namespaces.remove(global_namespace)
    namespaces.insert(0, global_namespace)

    for ns in namespaces:
        dupe_prefixes = find_duplicate_prefixes(apps, ns)

        # process tenants in order of number of related prefixes (fewest first)
        tenant_ids_sorted = (
            Prefix.objects.filter(namespace=ns)
            .values("tenant")
            .annotate(tenant_count=models.Count("tenant"))
            .order_by("tenant_count")
            .values_list("tenant", flat=True)
        )
        for dupe in dupe_prefixes:
            if "test" not in sys.argv:
                print(f">>> Processing Namespace migration for duplicate Prefix {dupe!r}")
            network, prefix_length = dupe.split("/")
            objects = Prefix.objects.filter(network=network, prefix_length=prefix_length, namespace=ns)
            # Leave the last instance of the Prefix in the original Namespace
            last_prefix = objects.filter(tenant_id=tenant_ids_sorted.last()).last()

            for tenant_id in tenant_ids_sorted:
                for _, prefix in enumerate(objects):
                    if prefix == last_prefix or prefix.tenant_id != tenant_id:
                        continue

                    namespace_base_name = BASE_NAME
                    if prefix.tenant is not None:
                        namespace_base_name += f" {prefix.tenant.name}"
                    prefix.namespace = get_next_prefix_cleanup_namespace(apps, prefix, base_name=namespace_base_name)
                    prefix.save()
                    if "test" not in sys.argv:
                        print(
                            f"    Prefix {dupe!r} migrated from Namespace {ns.name} to Namespace {prefix.namespace.name!r}"
                        )


def reparent_prefixes(apps):
    """
    Enumerate all Prefix objects in the database and attempt to find parent Prefix objects in the same Namespace.

    Args:
        apps: Django apps module

    Returns:
        None
    """
    Prefix = apps.get_model("ipam", "Prefix")

    if "test" not in sys.argv:
        print("\n>>> Processing Prefix parents, please standby...")
    for pfx in Prefix.objects.all().order_by("-prefix_length", "tenant"):
        try:
            parent = get_closest_parent(apps, pfx, pfx.namespace.prefixes.all())
            if pfx.namespace != parent.namespace:
                raise ValidationError("Prefix and parent are in different Namespaces")
            # TODO: useful but potentially very noisy. Do migrations have a verbosity option?
            # if "test" not in sys.argv:
            #     print(f">>> {pfx.network}/{pfx.prefix_length} parent: {parent.network}/{parent.prefix_length}")
            pfx.parent = parent
            pfx.save()
        except Prefix.DoesNotExist:
            continue


def copy_vrfs_to_cleanup_namespaces(apps):
    """
    Enumerate every Prefix with a non-null vrf and if the vrf namespace doesn't match the prefix namespace, make
    a copy of the vrf in the cleanup namespace.

    Args:
        apps: Django apps module

    Returns:
        None
    """

    IPAddress = apps.get_model("ipam", "IPAddress")
    Prefix = apps.get_model("ipam", "Prefix")
    VRF = apps.get_model("ipam", "VRF")
    Namespace = apps.get_model("ipam", "Namespace")

    for vrf in VRF.objects.all():
        if not vrf.prefixes.exclude(namespace=vrf.namespace).exists():
            continue

        namespaces = (
            vrf.prefixes.exclude(namespace=vrf.namespace).order_by().values_list("namespace", flat=True).distinct()
        )
        for namespace_pk in namespaces:
            namespace = Namespace.objects.get(pk=namespace_pk)
            if "test" not in sys.argv:
                print(f">>> Copying VRF {vrf.name!r} to namespace {namespace.name!r}")
            vrf_copy = VRF.objects.create(
                namespace=namespace,
                name=vrf.name,
                rd=vrf.rd,
                tenant=vrf.tenant,
                enforce_unique=vrf.enforce_unique,
                _custom_field_data=vrf._custom_field_data,
                description=DESCRIPTION,
            )
            vrf_copy.import_targets.set(vrf.import_targets.all())
            vrf_copy.export_targets.set(vrf.export_targets.all())
            Prefix.objects.filter(vrf=vrf, namespace_id=namespace_pk).update(vrf=vrf_copy)
            IPAddress.objects.filter(vrf=vrf, parent__namespace_id=namespace_pk).update(vrf=vrf_copy)


def process_interfaces(apps):
    """
    Process [VM]Interface objects.

    Args:
        apps: Django apps module

    Returns:
        None
    """
    Interface = apps.get_model("dcim", "Interface")
    VMInterface = apps.get_model("virtualization", "VMInterface")
    VRFDeviceAssignment = apps.get_model("ipam", "VRFDeviceAssignment")

    # Interfaces with vrfs
    ip_interfaces = Interface.objects.filter(ip_addresses__vrf__isnull=False)
    ip_vminterfaces = VMInterface.objects.filter(ip_addresses__vrf__isnull=False)

    # Case 2: Interface has one or more IP address assigned to it with no more than 1 distinct associated VRF (none is excluded)
    # The interface's VRF foreign key should be set to the VRF of any related IP Address with a non-null VRF.
    # The interface's parent device or virtual machine should adopt an assocation to the VRF (VRFDeviceAssignment) as well.
    for ifc in ip_interfaces:
        if "test" not in sys.argv:
            print(f">>> Processing VRF migration for numbered Interface {ifc.name!r}")
        # Set the Interface VRF to that of the first assigned IPAddress.
        first_ip = ifc.ip_addresses.filter(vrf__isnull=False).first()

        ifc_vrf = first_ip.vrf
        ifc.vrf = ifc_vrf
        ifc.save()

        # Create the VRF-to-device assignment.
        VRFDeviceAssignment.objects.get_or_create(vrf=ifc_vrf, device=ifc.device, rd=ifc_vrf.rd, name=ifc_vrf.name)

        if "test" not in sys.argv:
            print(f"    VRF {ifc_vrf.name!r} migrated from IPAddress {first_ip.host!r} to Interface {ifc.name!r}")

    # VirtualMachine should adopt an association to the VRF (VRFDeviceAssignment) as well.
    for ifc in ip_vminterfaces:
        if "test" not in sys.argv:
            print(f">>> Processing VRF migration for numbered VMInterface {ifc.name!r}")
        # Set the VMInterface VRF to that of the first assigned IPAddress.
        first_ip = ifc.ip_addresses.filter(vrf__isnull=False).first()

        ifc_vrf = first_ip.vrf
        ifc.vrf = ifc_vrf
        ifc.save()

        # Create the VRF-to-device assignment.
        VRFDeviceAssignment.objects.get_or_create(
            vrf=ifc_vrf, virtual_machine=ifc.virtual_machine, rd=ifc_vrf.rd, name=ifc_vrf.name
        )

        if "test" not in sys.argv:
            print(f"    VRF {ifc_vrf.name!r} migrated from IPAddress {first_ip.host!r} to VMInterface {ifc.name!r}")


def process_vrfs_prefixes_m2m(apps):
    """
    Convert the Prefix -> VRF FK relationship to a M2M relationship.

    Args:
        apps: Django apps module

    Returns:
        None
    """

    VRF = apps.get_model("ipam", "VRF")

    vrfs_with_prefixes = VRF.objects.filter(prefixes__isnull=False).order_by().distinct()

    for vrf in vrfs_with_prefixes:
        if "test" not in sys.argv:
            print(f"    Converting Prefix relationships to VRF {vrf.name} to M2M.")
        vrf.prefixes_m2m.set(vrf.prefixes.all())


def get_prefixes(qs):
    """
    Given a queryset, return the prefixes as 2-tuples of (network, prefix_length).

    Args:
        qs (QuerySet): QuerySet of Prefix objects.

    Returns:
        list
    """
    return sorted(qs.values_list("network", "prefix_length"))


def compare_prefix_querysets(a, b):
    """
    Compare two QuerySets of Prefix objects and return the set intersection of both.

    Args:
        a (QuerySet): Left-side QuerySet
        b (QuerySet): Right-side QuerySet

    Returns:
        set(tuple)
    """
    set_a = set(get_prefixes(a))
    set_b = set(get_prefixes(b))
    return set_a.intersection(set_b)


def create_vrf_namespace(apps, vrf):
    """
    Given a VRF, get or create a unique "VRF Namespace" for it.

    Args:
        apps: Django apps module
        vrf (VRF): VRF instance

    Returns:
        Namespace
    """
    Namespace = apps.get_model("ipam", "Namespace")
    base_name = f"VRF Namespace {vrf.name}"
    counter = 1
    created = False
    name = base_name
    while not created:
        ns, created = Namespace.objects.get_or_create(
            name=name,
            defaults={"description": DESCRIPTION},
        )
        counter += 1
        name = f"{base_name} ({counter})"

    return ns


def find_duplicate_prefixes(apps, namespace):
    """
    Return a list of duplicate prefixes for a given Namespace.

    Args:
        apps: Django apps module
        namespace (Namespace): Namespace instance

    Returns:
        list(str)
    """
    Prefix = apps.get_model("ipam", "Prefix")
    prefixes = Prefix.objects.filter(namespace=namespace).values_list("network", "prefix_length")
    counter = collections.Counter(prefixes)
    dupes = [p for p, cnt in counter.most_common() if cnt > 1]
    return [f"{network}/{prefix_length}" for network, prefix_length in dupes]


def generate_parent_prefix(apps, address):
    """
    For a given `address`, generate a containing parent network address.

    Args:
        apps: Django apps module
        address: Prefix/IPAddress instance or string

    Returns:
        netaddr.IPNetwork
    """
    cidr = validate_cidr(apps, address)
    return cidr.cidr


def get_closest_parent(apps, obj, qs):
    """
    This is forklifted from `Prefix.objects.get_closest_parent()` so that it can safely be used in
    migrations.

    Return the closest matching parent Prefix for a `cidr` even if it doesn't exist in the database.

    Args:
        obj: Prefix/IPAddress instance
        qs (QuerySet): QuerySet of Prefix objects

    Returns:
        Prefix or a filtered queryset
    """
    # Validate that it's a real CIDR
    cidr = validate_cidr(apps, obj)
    broadcast = str(cidr.broadcast or cidr.ip)

    Prefix = apps.get_model("ipam", "Prefix")
    IPAddress = apps.get_model("ipam", "IPAddress")

    # Prepare the queryset filter
    lookup_kwargs = {
        "ip_version": cidr.version,
        "network__lte": cidr.network,
        "broadcast__gte": broadcast,
    }

    if isinstance(obj, Prefix):
        lookup_kwargs["prefix_length__lt"] = cidr.prefixlen
        qs = qs.exclude(id=obj.id)
    else:
        lookup_kwargs["prefix_length__lte"] = cidr.prefixlen

    # Search for possible ancestors by network/prefix, returning them in
    # reverse prefix length order, so that we can choose the first one.
    possible_ancestors = (
        qs.filter(**lookup_kwargs)
        .annotate(
            custom_sort_order=models.Case(
                models.When(tenant=obj.tenant, vrf=obj.vrf, then=models.Value(1)),
                models.When(tenant__isnull=True, vrf=obj.vrf, then=models.Value(2)),
                models.When(tenant=obj.tenant, vrf__isnull=True, then=models.Value(3)),
                models.When(vrf=obj.vrf, then=models.Value(4)),
                models.When(tenant__isnull=True, vrf__isnull=True, then=models.Value(5)),
                models.When(vrf__isnull=True, then=models.Value(6)),
                default=models.Value(7),
            )
        )
        .order_by("-prefix_length", "custom_sort_order")
    )

    if isinstance(obj, IPAddress):
        # IP should not fall back to less specific prefixes
        if not possible_ancestors.exists():
            return qs.none()
        prefix_length = possible_ancestors.first().prefix_length
        return possible_ancestors.filter(prefix_length=prefix_length)

    # If we've got any matches, the first one is our closest parent.
    try:
        return possible_ancestors[0]
    except IndexError:
        raise Prefix.DoesNotExist(f"Could not determine parent Prefix for {cidr}")


def get_next_vrf_cleanup_namespace(apps, vrf):
    """
    Try to get the next available Cleanup Namespace based on `vrf` found in the "Global" Namespace.

    The Global Namespace is always scanned first to check for duplicates. If none are found then the
    Global Namespace will be returned, otherwise Cleanup Namespaces will be iterated until one
    without a duplicate is found. If a Namespace without duplicates cannot be found, a new one will
    be created.

    Args:
        apps: Django apps module
        vrf (VRF): VRF instance

    Returns:
        Namespace
    """
    Namespace = apps.get_model("ipam", "Namespace")
    VRF = apps.get_model("ipam", "VRF")

    counter = 1
    vrf_prefixes = vrf.prefixes.all()

    global_ns = Namespace.objects.get(name=GLOBAL_NS)
    global_ns_prefixes = global_ns.prefixes.exclude(vrf=vrf)
    global_dupe_prefixes = compare_prefix_querysets(vrf_prefixes, global_ns_prefixes)
    global_dupe_vrfs = VRF.objects.filter(namespace=global_ns, name=vrf.name).exclude(pk=vrf.pk).exists()

    if global_dupe_prefixes and "test" not in sys.argv:
        print(f"    VRF {vrf.name} has duplicate prefixes with NS {global_ns.name}")

    if global_dupe_vrfs and "test" not in sys.argv:
        print(f"    VRF {vrf.name} has duplicate VRF name with NS {global_ns.name}")

    if not any([global_dupe_prefixes, global_dupe_vrfs]):
        return global_ns

    # Iterate non-enforce_unique VRFS
    # - Compare duplicate prefixes for each VRF
    # - If a VRF has duplicates, it moves to a new namespace
    while True:
        base_name = f"{BASE_NAME} ({counter})"
        namespace, created = Namespace.objects.get_or_create(
            name=base_name,
            defaults={"description": DESCRIPTION},
        )
        if created:
            return namespace

        ns_prefixes = namespace.prefixes.exclude(vrf=vrf)
        dupe_prefixes = compare_prefix_querysets(vrf_prefixes, ns_prefixes)
        dupe_vrfs = VRF.objects.filter(namespace=namespace, name=vrf.name).exclude(pk=vrf.pk).exists()

        if dupe_prefixes and "test" not in sys.argv:
            print(f"    VRF {vrf.name} has duplicate prefixes with NS {namespace.name}")

        if dupe_vrfs and "test" not in sys.argv:
            print(f"    VRF {vrf.name} has duplicate VRF name with NS {namespace.name}")

        if any([dupe_prefixes, dupe_vrfs]):
            counter += 1
            continue

        return namespace


def get_next_prefix_cleanup_namespace(apps, prefix, base_name=BASE_NAME):
    """
    Try to ge the next avialable Cleanup Namespace based on `prefix` found in the "Global" Namespace.

    It is implied that the Prefix will be in the Global Namespace, so Cleanup Namespaces are
    automatically iterated to find a suitable match that has no duplicates. If a Namespace without
    duplicates cannot be found, a new one will be created.

    Args:
        apps: Django apps module
        prefix (Prefix): Prefix instance
        base_name (str): Base name to use for the Namespace

    Returns:
        Namespace
    """
    Namespace = apps.get_model("ipam", "Namespace")

    counter = 1
    while True:
        name = f"{base_name} ({counter})"
        namespace, created = Namespace.objects.get_or_create(
            name=name,
            defaults={"description": DESCRIPTION},
        )
        if created:
            return namespace

        has_dupe = namespace.prefixes.filter(network=prefix.network, prefix_length=prefix.prefix_length).exists()

        if has_dupe:
            # TODO: useful but potentially very noisy. Do migrations have a verbosity option?
            # if "test" not in sys.argv:
            #     cidr = f"{prefix.network}/{prefix.prefix_length}"
            #     print(f"    Prefix {cidr} is duplicated in NS {namespace.name}")
            counter += 1
            continue

        return namespace


def validate_cidr(apps, value):
    """
    Validate whether `value` is a valid IPv4/IPv6 CIDR.

    Args:
        value (str): IP address

    Returns:
        netaddr.IPNetwork
    """
    IPAddress = apps.get_model("ipam", "IPAddress")
    Prefix = apps.get_model("ipam", "Prefix")

    if isinstance(value, IPAddress):
        value = f"{value.host}/{value.prefix_length}"
    elif isinstance(value, Prefix):
        value = f"{value.network}/{value.prefix_length}"
    else:
        value = str(value)

    try:
        return netaddr.IPNetwork(value)
    except netaddr.AddrFormatError as err:
        raise ValidationError({"cidr": f"{value} does not appear to be an IPv4 or IPv6 network."}) from err


def ensure_correct_prefix_broadcast(apps):
    """
    Ensure that the prefix broadcast address is correct.

    Args:
        apps: Django apps module

    Returns:
        None
    """
    Prefix = apps.get_model("ipam", "Prefix")

    for prefix in Prefix.objects.all():
        true_broadcast = str(netaddr.IPNetwork(f"{prefix.network}/{prefix.prefix_length}")[-1])
        if prefix.broadcast != true_broadcast:
            if "test" not in sys.argv:
                print(
                    f"Updating {prefix.network}/{prefix.prefix_length} broadcast from {prefix.broadcast} to {true_broadcast}"
                )
            prefix.broadcast = true_broadcast
            prefix.save()


def increment_names_of_records_with_similar_names(model: models.Model):
    """
    This function increments the names of records with similar names in a given model.
    """
    cache = set()
    records_to_update = []
    for instance in model.objects.all().iterator():
        name = instance.name
        counter = 1
        while name in cache:
            suffix = f" {counter}"
            max_name_length = model.name.field.max_length - len(suffix)
            name = f"{instance.name[:max_name_length]}{suffix}"
            counter += 1

        if name != instance.name:
            print(f'   {model._meta.verbose_name} instance {instance.id} is being renamed to "{name}" for uniqueness')
            instance.name = name
            records_to_update.append(instance)
        cache.add(name)

    if records_to_update:
        model.objects.bulk_update(records_to_update, ["name"])
