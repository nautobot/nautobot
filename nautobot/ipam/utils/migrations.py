import collections

from django.core.exceptions import ValidationError
import netaddr


BASE_NAME = "Cleanup Namespace"


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


def get_next_prefix_namespace(apps, prefix):
    Namespace = apps.get_model("ipam", "Namespace")

    counter = 1
    while True:
        base_name = f"{BASE_NAME} ({counter})"
        namespaces = Namespace.objects.filter(name=base_name)

        if not namespaces.exists():
            return Namespace.objects.create(name=base_name, description="Created by Nautobot.")
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
    Validate whether `value` is a validr IPv4/IPv6 CIDR.

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


def get_closest_parent(apps, obj, namespace, max_prefix_length=0, tenant=None):
    """
    This is forklifted from `Prefix.objects.get_closest_parent()` so that it can safely be used in
    migrations.

    Return the closest matching parent Prefix for a `cidr` even if it doesn't exist in the database.

    Args:
        obj (str): IPv4/IPv6 CIDR string
        namespace (Namespace): Namespace instance
        max_prefix_length (int): Maximum prefix length depth for closest parent lookup
        tenant (Tenant): Tenant instance
    """
    # Validate that it's a real CIDR
    cidr = validate_cidr(apps, obj)
    broadcast = str(cidr.broadcast or cidr.ip)
    ip_version = cidr.version

    try:
        max_prefix_length = int(max_prefix_length)
    except ValueError:
        raise ValidationError({"max_prefix_length": f"Invalid prefix_length: {max_prefix_length}."})

    # Walk the supernets backwrds from smallest to largest prefix.
    try:
        supernets = cidr.supernet(prefixlen=max_prefix_length)
    except ValueError as err:
        raise ValidationError({"max_prefix_length": str(err)})
    else:
        supernets.reverse()

    # Enumerate all unique networks and prefixes
    networks = {str(s.network) for s in supernets}
    del supernets  # Free the memory because it could be quite large.

    IPAddress = apps.get_model("ipam", "IPAddress")
    Prefix = apps.get_model("ipam", "Prefix")

    # Prepare the queryset filter
    lookup_kwargs = {
        "network__in": networks,
        # TODO(jathan): This might be flawed if an IPAddress has a prefix_length that excludes it from a
        # parent that should otherwise contain it. If we encounter issues in the future for
        # identifying closest parent prefixes, this might be a starting point.
        "prefix_length__lte": cidr.prefixlen,
        "ip_version": ip_version,
        "broadcast__gte": broadcast,
        "namespace": namespace,
    }

    if obj.vrf is not None:
        lookup_kwargs["vrf"] = obj.vrf

    # Search for possible ancestors by network/prefix, returning them in reverse order, so that
    # we can choose the first one.
    possible_ancestors = Prefix.objects.filter(**lookup_kwargs).order_by("-prefix_length", "tenant")

    # Account for trying to pair up IPs with parent Prefixes that have matching Tenants. e.g. We
    # want this number to be as low as reasonably possible:
    # >>> IPAddress.objects.exclude(parent__tenant=F("tenant"))
    tenant_ancestors = possible_ancestors.filter(tenant=tenant)
    # if str(cidr) == "10.0.0.1/32":
    #    breakpoint()
    if tenant_ancestors.exists():
        # tenant_name = getattr(tenant, "name", "null")
        # print (f"    Matched Tenant {tenant_name!r} with possible ancestors for IPAddress {cidr}.")
        possible_ancestors = tenant_ancestors

    # If we've got any matches, the first one is our closest parent.
    try:
        return possible_ancestors[0]
    except IndexError:
        raise Prefix.DoesNotExist(f"Could not determine parent Prefix for {cidr}")


def generate_parent_prefix(apps, address):
    """For a given `address`, generate a containing parent network address."""
    cidr = validate_cidr(apps, address)
    return cidr.cidr


def process_namespaces(apps, schema_editor):
    print("\n", end="")

    # VRFs
    process_vrfs(apps)

    # Prefixes
    process_prefixes(apps)

    # Found/missing parents (IP, parent)
    # collected_ips = collect_ips(apps)

    # IPAddresses
    # process_ip_addresses(apps, collected_ips)
    process_ip_addresses(apps)

    # Matching/mismatched VRFs between IP/parent
    # collected_vrfs = collect_matching_vrfs(apps, collected_ips.found_parents)

    # [VM]Interfaces
    # process_interfaces(apps)


def process_vrfs(apps):
    VRF = apps.get_model("ipam", "VRF")
    vrfs = VRF.objects.all().order_by("name", "rd")
    unique_vrfs = vrfs.filter(enforce_unique=True)
    # These will all be in the Global NS
    non_unique_vrfs = vrfs.exclude(enforce_unique=True)

    # Case 0: VRFs with enforce_unique move to their own Namespace.
    # TODO(jathan): Should we also check for Prefix overlap here, too?
    for vrf in unique_vrfs:
        print(f">>> Processing migration for VRF {vrf.name!r}, Namespace {vrf.namespace.name!r}")
        vrf.namespace = create_vrf_namespace(apps, vrf)
        vrf.save()
        vrf.prefixes.update(namespace=vrf.namespace)
        print(f"    VRF {vrf.name!r} migrated to Namespace {vrf.namespace.name!r}")

    # Case 00: Unique fields vs. Namespaces (name/rd) move to a Cleanup Namespace.
    # Case 1 is not included here because it is a no-op.
    for vrf in non_unique_vrfs:
        print(f">>> Processing migration for VRF {vrf.name!r}, Namespace {vrf.namespace.name!r}")
        original_namespace = vrf.namespace
        vrf.namespace = get_next_cleanup_namespace(apps, vrf)
        vrf.save()
        vrf.prefixes.update(namespace=vrf.namespace)

        if vrf.namespace != original_namespace:
            print(f"    VRF {vrf.name!r} migrated from Namespace {original_namespace.name!r} to {vrf.namespace.name!r}")


def process_prefixes(apps):
    # By now we have asserted that the only Namespace that MAY have duplicate Prefixes is "Global".
    Namespace = apps.get_model("ipam", "Namespace")
    Prefix = apps.get_model("ipam", "Prefix")
    global_namespace = Namespace.objects.get(name="Global")
    dupe_prefixes = find_duplicate_prefixes(apps, global_namespace)

    for dupe in dupe_prefixes:
        print(f">>> Processing Namespace migration for duplicate Prefix {dupe!r}")
        network, prefix_length = dupe.split("/")
        objects = Prefix.objects.filter(network=network, prefix_length=prefix_length).order_by("tenant")

        for cnt, obj in enumerate(objects):
            # Skip the first one, to leave it in the Global Namespace. :|
            if cnt == 0:
                continue

            obj.namespace = get_next_prefix_namespace(apps, obj)
            obj.save()
            print(f"    Prefix {dupe!r} migrated from Global Namespace to Namespace {obj.namespace.name!r}")


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


# def process_ip_addresses(apps, collected_ips):
def process_ip_addresses(apps):
    """
    Enumerate collected IPs and parent them.

    - For IPs with found parents: Set that parent and save the `IPAddress`.
    - For orphand IPs (missing parents):
        - Generate a `Prefix` from the `IPAddress`
        - Get or create the parent `Prefix`
        - Set that as the parent and save the `IPAddress`

    """
    # Find the correct namespace for each IPAddress and move it if necessary.
    IPAddress = apps.get_model("ipam", "IPAddress")
    Prefix = apps.get_model("ipam", "Prefix")
    # found_parents, missing_parents = collected_ips
    found_parents, missing_parents = collect_ips(apps)

    # Explicitly set the parent for those that were found and save them.
    for found_ip, found_parent in found_parents:
        # TODO(jathan): Print message for parenting updates here (it's going to be noisy).
        found_ip.parent = found_parent
        found_ip.ip_version = found_parent.ip_version
        found_ip.save()

    # For IPs with no discovered parent, create one and assign it to the IP.
    for orphaned_ip in missing_parents:
        ip_repr = str(validate_cidr(apps, orphaned_ip))
        print(f">>> Processing Parent migration for orphaned IPAddress {ip_repr!r}")

        new_parent = generate_parent_prefix(apps, orphaned_ip)
        network = new_parent.network
        prefix_length = new_parent.prefixlen

        new_parent, _ = Prefix.objects.get_or_create(
            network=network,
            prefix_length=prefix_length,
            defaults={"description": "Created by Nautobot data migrations."},
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

    matching_vrfs, mismatched_vrfs = collected_vrfs
    mismatched_map = dict(mismatched_vrfs)

    # Numbered interfaces
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
