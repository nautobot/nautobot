from nautobot.core.apps import NautobotConfig


class IPAMConfig(NautobotConfig):
    default = True
    name = "nautobot.ipam"
    verbose_name = "IPAM"
    searchable_models = [
        "ipaddress",
        "namespace",
        "prefix",
        "vlan",
        "vrf",
    ]

    def ready(self):
        super().ready()

        from graphene_django.converter import convert_django_field, convert_field_to_string

        from nautobot.ipam.fields import VarbinaryIPField
        import nautobot.ipam.jobs
        import nautobot.ipam.signals  # noqa: F401  # unused-import -- but this import installs the signals

        # Register VarbinaryIPField to be converted to a string type
        convert_django_field.register(VarbinaryIPField)(convert_field_to_string)
