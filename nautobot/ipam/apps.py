from nautobot.core.apps import NautobotConfig


class IPAMConfig(NautobotConfig):
    name = "nautobot.ipam"
    verbose_name = "IPAM"

    def ready(self):
        super().ready()

        from graphene_django.converter import convert_django_field, convert_field_to_string
        from nautobot.ipam.fields import VarbinaryIPField

        # Register VarbinaryIPField to be converted to a string type
        convert_django_field.register(VarbinaryIPField)(convert_field_to_string)
