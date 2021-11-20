import graphene

from nautobot.core.apps import NautobotConfig


class DCIMConfig(NautobotConfig):
    name = "nautobot.dcim"
    verbose_name = "DCIM"

    def ready(self):
        super().ready()
        import nautobot.dcim.signals  # noqa: F401

        from graphene_django.converter import convert_django_field
        from nautobot.dcim.fields import MACAddressField

        @convert_django_field.register(MACAddressField)
        def convert_field_to_string(field, registry=None):
            """Convert MACAddressField to String."""
            return graphene.String()
