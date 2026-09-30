"""Field owners, read from Nautobot's own Object Metadata.

Core already models "who owns this field": an ``ObjectMetadata`` record on an object carries a contact or team
and a ``scoped_fields`` list (empty meaning every field). This module only reads those records.
"""

from dataclasses import dataclass
from typing import Any

from nautobot.extras.models import ObjectMetadata


@dataclass(frozen=True)
class Owner:
    """One Object Metadata record that applies to a field."""

    metadata_type: str
    owner: str
    owner_url: str | None
    value_display: str
    pk: Any

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable form used by the REST API."""
        return {
            "metadata_type": self.metadata_type,
            "owner": self.owner,
            "owner_url": self.owner_url,
            "value": self.value_display,
            "id": str(self.pk),
        }


def owners_for(obj, field_name: str, user=None) -> list[Owner]:
    """Return the Object Metadata records on ``obj`` whose scope includes ``field_name``."""
    queryset = ObjectMetadata.objects.get_for_object(obj).select_related("metadata_type", "contact", "team")
    if user is not None:
        queryset = queryset.restrict(user, "view")

    result: list[Owner] = []
    for metadata in queryset.order_by("metadata_type__name"):
        if metadata.scoped_fields and field_name not in metadata.scoped_fields:
            continue
        who = metadata.contact or metadata.team
        result.append(
            Owner(
                metadata_type=metadata.metadata_type.name,
                owner=str(who) if who is not None else "",
                owner_url=who.get_absolute_url() if who is not None else None,
                value_display="" if who is not None else str(metadata.get_value_display() or ""),
                pk=metadata.pk,
            )
        )
    return result
