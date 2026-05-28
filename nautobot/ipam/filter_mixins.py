import uuid

from nautobot.core.filters import NaturalKeyOrPKMultipleChoiceFilter
from nautobot.ipam import formfields
from nautobot.ipam.models import Prefix


class PrefixFilter(NaturalKeyOrPKMultipleChoiceFilter):
    """
    Filter that supports filtering a foreign key to Prefix by either its PK or by a literal `prefix` string.
    """

    field_class = formfields.PrefixFilterFormField

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("to_field_name", "pk")
        kwargs.setdefault("label", "Prefix (ID or prefix string)")
        kwargs.setdefault("queryset", Prefix.objects.all())
        super().__init__(*args, **kwargs)

    def get_filter_predicate(self, v):
        # Null value filtering
        if v is None:
            return {f"{self.field_name}__isnull": True}

        # If value is a model instance, stringify it to a pk.
        if isinstance(v, Prefix):
            v = v.pk

        # Try to cast the value to a UUID to distinguish between PKs and prefix strings
        v = str(v)
        try:
            uuid.UUID(v)
            return {self.field_name: v}
        except (AttributeError, TypeError, ValueError):
            # It's a prefix string
            prefixes_queryset = Prefix.objects.net_equals(v)
            return {f"{self.field_name}__in": prefixes_queryset.values_list("pk", flat=True)}
