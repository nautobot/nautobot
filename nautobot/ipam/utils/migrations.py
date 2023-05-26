import collections

from django.core.exceptions import ValidationError
from django.db import models
import netaddr


BASE_NAME = "Cleanup Namespace"


def process_namespaces(apps, schema_editor):
    print("\n", end="")

    # Fail if any interface or vm interface has IPs with different VRFs
    check_interface_vrfs(apps)

    # VRFs
    process_vrfs(apps)

    add_prefix_and_ip_address_version(apps)

    # IPAddresses
    # TODO: deduplicate IP addresses
    process_ip_addresses(apps)

    # Prefixes
    process_prefix_duplicates(apps)
    reparent_prefixes(apps)

    # [VM]Interfaces
    # process_interfaces(apps)

    # TODO(jathan): Make another pass across all Prefixes to duplicate a VRF if
    # it the namespace doesn't match (non-unique VRFs with duplicate Prefixes).
    # We'll need multiple Namespaces with that prefix + VRF(name, rd).


def check_interface_vrfs(apps):
    """
    Enumerate all Interface and VMInterface objects and raise an exception if any interface is found that is associated
    to more than one distinct VRF through the ip_address many-to-many relationship.
    """

    Interface = apps.get_model("dcim", "Interface")
    VMInterface = apps.get_model("virtualization", "VMInterface")

    interfaces_with_multiple_vrfs = Interface.objects.annotate(vrf_count=models.Count("ip_addresses__vrf")).filter(
        vrf_count__gt=1
    )
    vm_interfaces_with_multiple_vrfs = VMInterface.objects.annotate(vrf_count=models.Count("ip_addresses__vrf")).filter(
        vrf_count__gt=1
    )

    if interfaces_with_multiple_vrfs.exists() or vm_interfaces_with_multiple_vrfs.exists():
        raise Exception(
            "You cannot migrate Interfaces or VMInterfaces that have IPs with differing VRFs.",
            list(interfaces_with_multiple_vrfs),
            list(vm_interfaces_with_multiple_vrfs),
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
    global_ns_vrfs = vrfs.filter(namespace__name="Global")

    # Case 0: VRFs with enforce_unique move to their own Namespace.
    # TODO(jathan): Should we also check for Prefix overlap here, too?
    for vrf in unique_non_empty_vrfs:
        print(f">>> Processing migration for VRF {vrf.name!r}, Namespace {vrf.namespace.name!r}")
        vrf.namespace = create_vrf_namespace(apps, vrf)
        vrf.save()
        vrf.prefixes.update(namespace=vrf.namespace)
        print(f"    VRF {vrf.name!r} migrated to Namespace {vrf.namespace.name!r}")

    # Case 00: Unique fields vs. Namespaces (name/rd) move to a Cleanup Namespace.
    # Case 1 is not included here because it is a no-op.
    for vrf in global_ns_vrfs.annotate(prefix_count=models.Count("prefixes")).order_by("-prefix_count"):
        print(f">>> Processing migration for VRF {vrf.name!r}, Namespace {vrf.namespace.name!r}")
        original_namespace = vrf.namespace
        vrf.namespace = get_next_cleanup_namespace(apps, vrf)
        vrf.save()
        if vrf.namespace != original_namespace:
            vrf.prefixes.update(namespace=vrf.namespace)
            print(f"    VRF {vrf.name!r} migrated from Namespace {original_namespace.name!r} to {vrf.namespace.name!r}")


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
    global_namespace = Namespace.objects.get(name="Global")

    namespaces = list(Namespace.objects.all())
    # Always start with the Global Namespace.
    namespaces.remove(global_namespace)
    namespaces.insert(0, global_namespace)

    for ns in namespaces:
        # move prefixes without a tenant on the second pass if necessary
        for tenant_isnull in (False, True):
            dupe_prefixes = find_duplicate_prefixes(apps, ns)

            for dupe in dupe_prefixes:
                print(f">>> Processing Namespace migration for duplicate Prefix {dupe!r}")
                network, prefix_length = dupe.split("/")
                objects = Prefix.objects.filter(
                    network=network, prefix_length=prefix_length, tenant__isnull=tenant_isnull, namespace=ns
                ).order_by("tenant")

                for _, obj in enumerate(objects):
                    # Leave the last instance of the Prefix in the Namespace
                    prefix_count = Prefix.objects.filter(
                        namespace=ns, network=obj.network, prefix_length=obj.prefix_length
                    ).count()
                    if prefix_count == 1:
                        continue

                    base_name = "Cleanup Namespace"
                    if not tenant_isnull:
                        base_name += f" {obj.tenant.name}"
                    obj.namespace = get_next_prefix_namespace(apps, obj, base_name=base_name)
                    obj.save()
                    print(f"    Prefix {dupe!r} migrated from Namespace {ns.name} to Namespace {obj.namespace.name!r}")


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

    print(">>> Populating Prefix.ip_version field")
    for pfx in Prefix.objects.all():
        cidr = validate_cidr(apps, pfx)
        pfx.ip_version = cidr.version
        pfx.save()

    print(">>> Populating IPAddress.ip_version field")
    for ip in IPAddress.objects.all():
        cidr = validate_cidr(apps, ip)
        ip.ip_version = cidr.version
        ip.save()


def reparent_prefixes(apps):
    """
    Enumerate all Prefix objects in the database and attempt to find parent Prefix objects in the same Namespace.

    Args:
        apps: Django apps module

    Returns:
        None
    """
    Prefix = apps.get_model("ipam", "Prefix")

    print("\n>>> Processing Prefix parents, please standby...")
    for pfx in Prefix.objects.all().order_by("-prefix_length", "tenant"):
        try:
            parent = get_closest_parent(apps, pfx, pfx.namespace.prefixes.all())
            if pfx.namespace != parent.namespace:
                raise Exception("Prefix and parent are in different Namespaces")
            print(f"\n>>> {pfx.network}/{pfx.prefix_length} parent: {parent.network}/{parent.prefix_length}")
            pfx.parent = parent
            pfx.save()
        except Prefix.DoesNotExist:
            continue


def get_next_cleanup_namespace(apps, vrf):
    """
    Try to get the next available Cleanup Namespace based on `vrf`.

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

    global_ns = Namespace.objects.get(name="Global")
    global_ns_prefixes = global_ns.prefixes.exclude(vrf=vrf)
    global_dupe_prefixes = compare_duplicate_prefixes(vrf_prefixes, global_ns_prefixes)
    global_dupe_vrfs = VRF.objects.filter(namespace=global_ns, name=vrf.name).exclude(pk=vrf.pk).exists()

    if global_dupe_prefixes:
        print(f"    VRF {vrf.name} has duplicate prefixes with NS {global_ns.name}")

    if global_dupe_vrfs:
        print(f"    VRF {vrf.name} has duplicate VRF name with NS {global_ns.name}")

    if not any([global_dupe_prefixes, global_dupe_vrfs]):
        return global_ns

    # Iterate non-enforce_unique VRFS
    # - Compare duplicate prefixes for each VRF
    # - If a VRF has duplicates, it moves to a new namespace
    while True:
        base_name = f"{BASE_NAME} ({counter})"
        namespaces = Namespace.objects.filter(name=base_name)

        if not namespaces.exists():
            return Namespace.objects.create(name=base_name, description="Created by Nautobot.")
        namespace = namespaces.get()
        ns_prefixes = namespace.prefixes.exclude(vrf=vrf)
        dupe_prefixes = compare_duplicate_prefixes(vrf_prefixes, ns_prefixes)
        dupe_vrfs = VRF.objects.filter(namespace=namespace, name=vrf.name).exclude(pk=vrf.pk).exists()

        if dupe_prefixes:
            print(f"    VRF {vrf.name} has duplicate prefixes with NS {namespace.name}")

        if dupe_vrfs:
            print(f"    VRF {vrf.name} has duplicate VRF name with NS {namespace.name}")

        if any([dupe_prefixes, dupe_vrfs]):
            counter += 1
            continue

        return namespace


def get_next_prefix_namespace(apps, prefix, base_name=BASE_NAME):
    Namespace = apps.get_model("ipam", "Namespace")

    counter = 1
    while True:
        name = f"{base_name} ({counter})"
        namespaces = Namespace.objects.filter(name=name)

        if not namespaces.exists():
            return Namespace.objects.create(name=name, description="Created by Nautobot.")
        namespace = namespaces.get()
        cidr = f"{prefix.network}/{prefix.prefix_length}"
        has_dupe = namespace.prefixes.filter(network=prefix.network, prefix_length=prefix.prefix_length).exists()

        if has_dupe:
            print(f"    Prefix {cidr} is duplicated in NS {namespace.name}")
            counter += 1
            continue

        return namespace


def create_vrf_namespace(apps, vrf):
    Namespace = apps.get_model("ipam", "Namespace")
    base_name = f"VRF Namespace {vrf.name}"
    counter = 1
    created = False
    name = base_name
    while not created:
        ns, created = Namespace.objects.get_or_create(
            name=name,
            defaults={"description": "Created by Nautobot."},
        )
        counter += 1
        name = f"{base_name} ({counter})"

    return ns


def get_prefixes(qs):
    return sorted(qs.values_list("network", "prefix_length"))


def compare_duplicate_prefixes(a, b):
    set_a = set(get_prefixes(a))
    set_b = set(get_prefixes(b))
    return set_a.intersection(set_b)


def find_duplicate_prefixes(apps, namespace):
    Prefix = apps.get_model("ipam", "Prefix")
    prefixes = Prefix.objects.filter(namespace=namespace).values_list("network", "prefix_length")
    counter = collections.Counter(prefixes)
    dupes = [p for p, cnt in counter.most_common() if cnt > 1]
    return [f"{network}/{prefix_length}" for network, prefix_length in dupes]


def compare_duplicate_ips(a, b):
    set_a = set(a.values_list("host", "prefix_length"))
    set_b = set(b.values_list("host", "prefix_length"))
    return set_a.intersection(set_b)


def find_duplicate_ips(apps):
    IPAddress = apps.get_model("ipam", "IPAddress")
    ips = IPAddress.objects.values_list("host", "prefix_length")
    counter = collections.Counter(ips)
    dupes = [p for p, cnt in counter.most_common() if cnt > 1]
    return [f"{host}/{prefix_length}" for host, prefix_length in dupes]


def validate_cidr(apps, value):
    """
    Validate whether `value` is a valid IPv4/IPv6 CIDR.

    Args:
        value (str): IP address
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


def get_closest_parent(apps, obj, qs):
    """
    This is forklifted from `Prefix.objects.get_closest_parent()` so that it can safely be used in
    migrations.

    Return the closest matching parent Prefix for a `cidr` even if it doesn't exist in the database.

    Args:
        obj: Prefix/IPAddress instance
        namespace (Namespace): Namespace instance
        max_prefix_length (int): Maximum prefix length depth for closest parent lookup
        tenant (Tenant): Tenant instance
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


def generate_parent_prefix(apps, address):
    """For a given `address`, generate a containing parent network address."""
    cidr = validate_cidr(apps, address)
    return cidr.cidr


CollectedIPs = collections.namedtuple("CollectedIPs", "found_parents missing_parents")


def collect_ips(apps):
    """
    Enumerate all IPAddress objects in the database and cycle through Namespaces, starting with the
    "Global" Namespace to attempt to map IPs to parent Prefix objects in a Namespace.

    This will bucket them into IPs with "found" and "missing" parents.

    Args:
        apps: Django apps module

    Returns:
        ColllectedIPs
    """
    IPAddress = apps.get_model("ipam", "IPAddress")
    Namespace = apps.get_model("ipam", "Namespace")
    Prefix = apps.get_model("ipam", "Prefix")
    found_parents = []
    missing_parents = []

    # TODO(jathan): This could be very memory intensive; we might want to stash these in Redis/shelve
    namespaces = list(Namespace.objects.all())
    global_namespace = Namespace.objects.get(name="Global")
    # Always start with the Global Namespace.
    namespaces.remove(global_namespace)
    namespaces.insert(0, global_namespace)

    print("\n>>> Processing IPAddresses, please standby...")
    for ip in IPAddress.objects.all().order_by("tenant"):
        for namespace in namespaces:
            try:
                parent = get_closest_parent(apps, ip, namespace=namespace, tenant=ip.tenant)
            except Prefix.DoesNotExist:
                continue
            else:
                found_parents.append((ip, parent))
                break
        else:
            missing_parents.append(ip)

    return CollectedIPs(found_parents, missing_parents)


def process_ip_addresses(apps):
    """
    Enumerate collected IPs and parent them.

    - For IPs with found parents: Set that parent and save the `IPAddress`.
    - For orphaned IPs (missing parents):
        - Generate a `Prefix` from the `IPAddress`
        - Get or create the parent `Prefix`
        - Set that as the parent and save the `IPAddress`

    """
    # Find the correct namespace for each IPAddress and move it if necessary.
    IPAddress = apps.get_model("ipam", "IPAddress")
    Namespace = apps.get_model("ipam", "Namespace")
    Prefix = apps.get_model("ipam", "Prefix")

    # Explicitly set the parent for those that were found and save them.
    for ip in IPAddress.objects.filter(parent__isnull=True).order_by("-vrf", "-tenant"):
        # TODO(jathan): Print message for parenting updates here (it's going to be noisy).
        potential_parents = get_closest_parent(apps, ip, Prefix.objects.all())
        for prefix in potential_parents:
            if not prefix.ip_addresses.filter(host=ip.host).exists():
                ip.parent = prefix
                ip.ip_version = prefix.ip_version
                ip.save()
                break

    # For IPs with no discovered parent, create one and assign it to the IP.
    global_ns = Namespace.objects.get(name="Global")
    for orphaned_ip in IPAddress.objects.filter(parent__isnull=True):
        ip_repr = str(validate_cidr(apps, orphaned_ip))
        print(f">>> Processing Parent migration for orphaned IPAddress {ip_repr!r}")

        new_parent = generate_parent_prefix(apps, orphaned_ip)
        network = new_parent.network
        prefix_length = new_parent.prefixlen
        potential_parents = Prefix.objects.filter(network=network, prefix_length=prefix_length).exclude(
            ip_addresses__host=orphaned_ip.host
        )
        if potential_parents.exists():
            new_parent = potential_parents.first()

        else:
            new_parent = Prefix.objects.create(
                network=network,
                tenant=orphaned_ip.tenant,
                vrf=orphaned_ip.vrf,
                prefix_length=prefix_length,
                namespace=global_ns,
                description="Created by Nautobot data migrations.",
            )
        orphaned_ip.parent = new_parent
        orphaned_ip.ip_version = new_parent.ip_version
        orphaned_ip.save()

        parent_repr = str(validate_cidr(apps, new_parent))
        print(
            f"    IPAddress {ip_repr!r} migrated to Parent Prefix {parent_repr!r} in Namespace {new_parent.namespace.name!r}"
        )

    # By this point we should arrive at NO orphaned IPAddress objects.
    if IPAddress.objects.filter(parent__isnull=True).exists():
        raise SystemExit("OH NOES we still have orphaned IPs! Stop everything and find out why!")


CollectedVRFs = collections.namedtuple("CollectedVRFs", "matching_vrfs mismatched_vrfs")


def collect_matching_vrfs(apps, found_parents):
    """Return a list of good/bad IPs/parents where VRFs are matched or not."""
    matching_vrfs = []
    mismatched_vrfs = []

    for ip, parent in found_parents:
        if ip.vrf and (ip.vrf != parent.vrf):
            mismatched_vrfs.append((ip, parent))
        elif ip.vrf == parent.vrf:
            matching_vrfs.append((ip, parent))
        else:
            raise RuntimeError("Unexpected parent/child VRF situation. Call the police.")

    return CollectedVRFs(matching_vrfs, mismatched_vrfs)


def has_mismatched_parent_vrf(ip):
    if ip.vrf is not None:
        return ip.vrf.prefixes.filter(pk=ip.parent.pk).exists()
    return False


def process_interfaces(apps, collected_vrfs):
    """Process [VM]Interface objects."""
    Interface = apps.get_model("dcim", "Interface")
    VMInterface = apps.get_model("virtualization", "VMInterface")
    VRFDeviceAssignment = apps.get_model("ipam", "VRFDeviceAssignment")

    # Interfaces with vrfs
    ip_interfaces = Interface.objects.filter(ip_addresses__vrf__isnull=False)
    ip_vminterfaces = VMInterface.objects.filter(ip_addresses__vrf__isnull=False)

    # TODO(jathan): We need to also account for whether that IP's parent does not have a conflict
    # where the parent's VRF doesn't match the VRF of the IPAddress assigned to the [VM]Interface.

    # Case 2: Interface has one or more IP address assigned to it that result in a single assigned
    # VRF (none is excluded) to its Interface should adopt the VRF of the IP Address assigned to it,
    # Device should adopt an assocation to the VRF (VRFDeviceAssignment) as well.
    for ifc in ip_interfaces:
        print(f">>> Processing VRF migration for numbered Interface {ifc.name!r}")
        # Case 3: Interface has many IP addresses assigned to it with different VRFs = ???
        if ifc.ip_addresses.values_list("vrf", flat=True).count() > 1:
            raise SystemExit("You cannot migrate Interfaces that have IPs with differing VRFs.")

        # Set the Interface VRF to that of the first assigned IPAddress.
        first_ip = ifc.ip_addresses.first()
        # if has_mismatched_parent_vrf(first_ip):
        #     raise SystemExit("You cannot migrate Interfaces that have IPs with conflicting VRFs between with the parent Prefix.")

        ifc_vrf = first_ip.vrf
        ifc.vrf = ifc_vrf
        ifc.save()

        # Create the VRF-to-device assignment.
        VRFDeviceAssignment.objects.create(vrf=ifc_vrf, device=ifc.device, rd=ifc_vrf.rd, name=ifc_vrf.name)

        print(f"    VRF {ifc_vrf.name!r} migrated from IPAddress {first_ip.host!r} to Interface {ifc.name!r}")

    # VirtualMachine should adopt an association to the VRF (VRFDeviceAssignment) as well.
    for ifc in ip_vminterfaces:
        print(f">>> Processing VRF migration for numbered VMInterface {ifc.name!r}")
        # Case 3: Interface has many IP addresses assigned to it with different VRFs = ???
        if ifc.ip_addresses.values_list("vrf", flat=True).count() > 1:
            raise SystemExit("You cannot migrate VMInterfaces that have IPs with differing VRFs.")

        # Set the VMInterface VRF to that of the first assigned IPAddress.
        first_ip = ifc.ip_addresses.first()
        # if has_mismatched_parent_vrf(first_ip):
        #     raise SystemExit("You cannot migrate VMInterfaces that have IPs with conflicting VRFs between with the parent Prefix.")

        ifc_vrf = first_ip.vrf
        ifc.vrf = ifc_vrf
        ifc.save()

        # Create the VRF-to-device assignment.
        VRFDeviceAssignment.objects.create(
            vrf=ifc_vrf, virtual_machine=ifc.virtual_machine, rd=ifc_vrf.rd, name=ifc_vrf.name
        )

        print(f"    VRF {ifc_vrf.name!r} migrated from IPAddress {first_ip.host!r} to VMInterface {ifc.name!r}")


def _test_sort(qs, tree_node):
    return (
        qs.filter(
            network__lte=tree_node.obj.network,
            broadcast__gte=tree_node.obj.broadcast,
            prefix_length__lt=tree_node.obj.prefix_length,
        )
        .annotate(
            custom_sort_order=models.Case(
                models.When(tenant=tree_node.tenant, vrf=tree_node.vrf, then=models.Value(1)),
                models.When(tenant__isnull=True, vrf=tree_node.vrf, then=models.Value(2)),
                models.When(tenant=tree_node.tenant, vrf__isnull=True, then=models.Value(3)),
                models.When(vrf=tree_node.vrf, then=models.Value(4)),
                models.When(tenant__isnull=True, vrf__isnull=True, then=models.Value(5)),
                models.When(vrf__isnull=True, then=models.Value(6)),
                default=models.Value(7),
            )
        )
        .filter(custom_sort_order__lt=7)
        .order_by("-prefix_length", "custom_sort_order")
    )
