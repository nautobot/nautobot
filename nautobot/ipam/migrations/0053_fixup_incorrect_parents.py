from django.db import migrations, models
import netaddr


def fixup_incorrect_parents(apps, schema):
    IPAddress = apps.get_model("ipam", "IPAddress")
    Prefix = apps.get_model("ipam", "Prefix")

    failed = False

    wrong_ip_parents = (
        IPAddress.objects.filter(
            models.Q(parent__network__gt=models.F("host"))
            | models.Q(parent__broadcast__lt=models.F("host"))
            | models.Q(parent__isnull=True)
        )
        | IPAddress.objects.exclude(parent__ip_version=models.F("ip_version"))
    ).select_related("parent")

    from nautobot.ipam.models import get_default_namespace_pk

    # based on PrefixQuerySet.get_closest_parent()
    for ip in wrong_ip_parents:
        cidr = netaddr.IPNetwork(ip.host)
        broadcast = str(cidr.broadcast or cidr.ip)
        parent = (
            Prefix.objects.filter(
                network__lte=cidr.value,
                broadcast__gte=broadcast,
                ip_version=cidr.version,
                namespace_id=ip.parent.namespace_id if ip.parent is not None else get_default_namespace_pk(),
            )
            .order_by("-prefix_length")
            .first()
        )
        if parent is not None:
            ip.parent = parent
        else:
            print(f"    No valid parent Prefix found for {ip.host} in namespace {ip.parent.namespace.name}")
            failed = True

    ip_count = IPAddress.objects.bulk_update(wrong_ip_parents, ["parent"], batch_size=1000)
    print(f"    >>> Inspected {wrong_ip_parents.count()} and corrected invalid parent for {ip_count} IPAddresses")

    maybe_wrong_prefix_parents = (
        Prefix.objects.filter(
            models.Q(parent__network__gt=models.F("network"))
            | models.Q(parent__broadcast__lt=models.F("broadcast"))
            | models.Q(parent__prefix_length__gte=models.F("prefix_length"))
            | models.Q(parent__isnull=True)  # not necessarily wrong, but worth checking
        )
        | Prefix.objects.exclude(parent__ip_version=models.F("ip_version"))
        | Prefix.objects.exclude(parent__namespace_id=models.F("namespace_id"))
    ).select_related("parent")

    # TODO: distinct?

    wrong_prefix_parents = []

    for pfx in maybe_wrong_prefix_parents:
        parent = (
            Prefix.objects.filter(
                network__lte=pfx.network,
                broadcast__gte=pfx.broadcast,
                prefix_length__lt=pfx.prefix_length,
                ip_version=pfx.ip_version,
                namespace_id=pfx.namespace_id,
            )
            .order_by("-prefix_length")
            .first()
        )
        if parent != pfx.parent:
            pfx.parent = parent
            wrong_prefix_parents.append(pfx)

    pfx_count = Prefix.objects.bulk_update(wrong_prefix_parents, ["parent"], batch_size=1000)
    print(
        f"    >>> Inspected {maybe_wrong_prefix_parents.count()} and corrected invalid parent for {pfx_count} Prefixes"
    )

    # Blunter force approach to capture cases like:
    # 10.0.0.0/8 (Prefix)
    #   10.1.1.1/24 (IPAddress)
    #   10.1.1.0/24 (Prefix)
    # where the IPAddress parent is a valid but not most-specific Prefix.
    imprecise_ip_parents = []
    processed_ip_count = 0
    for pfx in Prefix.objects.filter(ip_addresses__isnull=False, children__isnull=False).distinct():
        # based on PrefixQuerySet.get_closest_parent()
        for ip in pfx.ip_addresses.all():
            cidr = netaddr.IPNetwork(ip.host)
            broadcast = str(cidr.broadcast or cidr.ip)
            parent = (
                Prefix.objects.filter(
                    network__lte=cidr.value,
                    broadcast__gte=broadcast,
                    ip_version=cidr.version,
                    namespace_id=ip.parent.namespace_id if ip.parent is not None else get_default_namespace_pk(),
                )
                .order_by("-prefix_length")
                .first()
            )
            if parent.id != ip.parent_id:
                ip.parent = parent
                imprecise_ip_parents.append(ip)
            processed_ip_count += 1

    ip_count = IPAddress.objects.bulk_update(imprecise_ip_parents, ["parent"], batch_size=1000)
    print(f"    >>> Inspected {processed_ip_count} and corrected inaccurate parent for {ip_count} IPAddresses")

    # Similarly for cases like:
    # 10.0.0.0/8 (Prefix)
    #   10.1.1.0/24 (Prefix)
    #   10.1.0.0/16 (Prefix)
    imprecise_prefix_parents = []
    processed_pfx_count = 0
    for pfx in Prefix.objects.filter(children__prefix_length__gt=models.F("prefix_length") + 1).distinct():
        for child_pfx in pfx.children.filter(prefix_length__gt=pfx.prefix_length + 1).distinct():
            parent = (
                Prefix.objects.filter(
                    network__lte=child_pfx.network,
                    broadcast__gte=child_pfx.broadcast,
                    prefix_length__lt=child_pfx.prefix_length,
                    ip_version=child_pfx.ip_version,
                    namespace_id=child_pfx.namespace_id,
                )
                .order_by("-prefix_length")
                .first()
            )
            if parent != child_pfx.parent:
                child_pfx.parent = parent
                imprecise_prefix_parents.append(child_pfx)
            processed_pfx_count += 1

    pfx_count = Prefix.objects.bulk_update(imprecise_prefix_parents, ["parent"], batch_size=1000)
    print(f"    >>> Inspected {processed_pfx_count} and corrected inaccurate parent for {pfx_count} Prefixes")

    if failed:
        raise RuntimeError("Not all parent values could be corrected. You may need to manually create some records.")


class Migration(migrations.Migration):
    dependencies = [
        ("ipam", "0052_alter_ipaddress_index_together_and_more"),
    ]

    operations = [migrations.RunPython(fixup_incorrect_parents, migrations.RunPython.noop)]
