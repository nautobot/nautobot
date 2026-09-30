"""Join the row set, the changelog replay, and the owners into one record per field."""

from dataclasses import dataclass
from typing import Any

from django.contrib.contenttypes.models import ContentType
from nautobot.extras.models import ObjectChange

from nautobot.extras.provenance import fields, history, owners

DEFAULT_LIMIT = 10


def object_changes(obj, user=None) -> list[ObjectChange]:
    """Return the changelog of ``obj`` oldest first, limited to what ``user`` may view."""
    content_type = ContentType.objects.get_for_model(obj)
    queryset = ObjectChange.objects.filter(changed_object_type=content_type, changed_object_id=obj.pk)
    if user is not None:
        queryset = queryset.restrict(user, "view")
    return list(queryset.order_by("time"))


@dataclass
class FieldSummary:
    """Everything the Provenance tab shows for one field of one object."""

    obj: Any
    row: fields.FieldRow
    current: fields.DisplayValue
    history: history.FieldHistory
    owners: list[owners.Owner]

    def __str__(self) -> str:
        """The field label; core's row toggle uses it in its "Show details for ..." title."""
        return self.row.label

    @property
    def pk(self) -> str:
        """Row identity for the table and the expandable row id (``overview-<name>``)."""
        return self.row.name

    @property
    def name(self) -> str:
        """The form field name."""
        return self.row.name

    @property
    def app_label(self) -> str:
        """App label of the object's model, for URL reversing."""
        return self.obj._meta.app_label

    @property
    def model_name(self) -> str:
        """Model name of the object's model, for URL reversing."""
        return self.obj._meta.model_name

    @property
    def object_pk(self):
        """Primary key of the object, for URL reversing."""
        return self.obj.pk

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable form used by the REST API."""
        return {
            "field": self.row.to_dict(),
            "current": self.current.to_dict(),
            "history": self.history.to_dict(),
            "owners": [owner.to_dict() for owner in self.owners],
        }


def _summarize(obj, row, changes, user, limit) -> FieldSummary:
    if row.tracked:
        field_history = history.field_history(changes, row.path, limit=limit)
    else:
        field_history = history.FieldHistory(entries=[], change_count=0, truncated=False)
    return FieldSummary(
        obj=obj,
        row=row,
        current=fields.current_value(obj, row),
        history=field_history,
        owners=owners.owners_for(obj, row.name, user=user),
    )


def summaries_for(obj, user=None, limit: int = DEFAULT_LIMIT) -> list[FieldSummary]:
    """Return one FieldSummary per Provenance row of ``obj``."""
    changes = object_changes(obj, user=user)
    return [_summarize(obj, row, changes, user, limit) for row in fields.rows_for(type(obj))]


def summary_for_field(obj, field_name: str, user=None, limit: int = DEFAULT_LIMIT) -> FieldSummary | None:
    """Return the FieldSummary for one row of ``obj``, or None when the model has no such row."""
    for row in fields.rows_for(type(obj)):
        if row.name == field_name:
            return _summarize(obj, row, object_changes(obj, user=user), user, limit)
    return None
