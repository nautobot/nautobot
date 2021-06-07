from django.db import migrations

import netaddr


def fixup_p2p_broadcast(apps, schema_editor):
    """Correct the "broadcast" field for /31 and /127, as per https://github.com/nautobot/nautobot/pull/509."""
    Aggregate = apps.get_model("ipam", "Aggregate")
    Prefix = apps.get_model("ipam", "Prefix")
    IPAddress = apps.get_model("ipam", "IPAddress")

    # If the above models were our actual fully-implemented IPAM model classes, we could simply
    # call model.prefix = model.prefix to force recalculation of the broadcast address,
    # but the models we have access to here do not have any custom methods available.
    # So we have to fixup the broadcast addresses ourselves.

    for prefixlen in (31, 127):
        for aggregate in Aggregate.objects.filter(prefix_length=prefixlen):
            network = netaddr.IPNetwork(f"{aggregate.network}/{aggregate.prefix_length}")
            # Last address in the network is our "broadcast" address.
            aggregate.broadcast = network[-1]
            aggregate.save()

        for prefix in Prefix.objects.filter(prefix_length=prefixlen):
            network = netaddr.IPNetwork(f"{prefix.network}/{prefix.prefix_length}")
            # Last address in the network is our "broadcast" address.
            prefix.broadcast = network[-1]
            prefix.save()

        for ipaddress in IPAddress.objects.filter(prefix_length=prefixlen):
            network = netaddr.IPNetwork(f"{ipaddress.host}/{ipaddress.prefix_length}")
            # Last address in the network is our "broadcast" address.
            ipaddress.broadcast = network[-1]
            ipaddress.save()


class Migration(migrations.Migration):

    dependencies = [
        ("ipam", "0003_remove_max_length"),
    ]

    operations = [
        migrations.RunPython(
            code=fixup_p2p_broadcast,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
