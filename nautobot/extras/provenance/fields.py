"""Decide which fields the Provenance tab lists for a model, and how each value displays.

The row set is the model's edit form: the same fields, in the same order and with the same labels a user
sees on Add/Edit. Each row maps to a dotted path in the changelog snapshot, or to nothing when the value is
not recorded there (relationships).
"""

import logging
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from functools import lru_cache
from typing import Any

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.http import Http404
from django.urls import NoReverseMatch
from nautobot.extras.models.change_logging import ChangeLoggedModel
from nautobot.core.utils.lookup import get_form_for_model

logger = logging.getLogger(__name__)

KIND_SCALAR = "scalar"
KIND_OBJECT = "object"
KIND_LIST = "list"
KIND_JSON = "json"
KIND_UNTRACKED = "untracked"

CUSTOM_FIELD_PREFIX = "cf_"
RELATIONSHIP_PREFIX = "cr_"


@dataclass(frozen=True)
class FieldRow:
    """One row of the Provenance table: a form field and where it lives in a snapshot."""

    name: str
    label: str
    path: str | None
    kind: str

    @property
    def pk(self) -> str:
        """Row identity used for HTML ids; the form field name is unique per model."""
        return self.name

    @property
    def tracked(self) -> bool:
        """Return True when the changelog snapshot records this field."""
        return self.path is not None

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable form used by the REST API."""
        return {"name": self.name, "label": self.label, "path": self.path, "kind": self.kind, "tracked": self.tracked}


@dataclass
class DisplayValue:
    """A value prepared for display: what to show, where it links, and the raw data behind it."""

    kind: str
    text: str = ""
    url: str | None = None
    items: list["DisplayValue"] = dataclass_field(default_factory=list)
    data: Any = None

    def to_dict(self) -> Any:
        """Return the JSON-serializable form used by the REST API."""
        if self.kind == KIND_OBJECT:
            return {"display": self.text, "url": self.url}
        if self.kind == KIND_LIST:
            return [item.to_dict() for item in self.items]
        if self.kind == KIND_UNTRACKED:
            return None
        return self.data


def _kind_for_model_field(model_field) -> str:
    if isinstance(model_field, models.JSONField):
        return KIND_JSON
    if model_field.many_to_many:
        return KIND_LIST
    if model_field.is_relation:
        return KIND_OBJECT
    return KIND_SCALAR


def rows_for(model) -> list[FieldRow]:
    """Return the Provenance rows for ``model``, derived from its edit form."""
    form_class = get_form_for_model(model)
    if form_class is None:
        return []
    try:
        form = form_class()
    except TypeError:
        logger.debug("Form %s needs arguments; no provenance rows for %s", form_class, model)
        return []

    rows: list[FieldRow] = []
    for name, form_field in form.fields.items():
        label = str(form_field.label) if form_field.label else name.replace("_", " ").capitalize()
        if name.startswith(CUSTOM_FIELD_PREFIX):
            rows.append(FieldRow(name, label, f"custom_fields.{name[len(CUSTOM_FIELD_PREFIX):]}", KIND_SCALAR))
            continue
        if name.startswith(RELATIONSHIP_PREFIX):
            rows.append(FieldRow(name, label, None, KIND_UNTRACKED))
            continue
        try:
            model_field = model._meta.get_field(name)
        except FieldDoesNotExist:
            continue  # form-only helper such as object_note or a parent-object picker
        if model_field.auto_created and not model_field.concrete:
            continue  # reverse relation exposed on the form for convenience; not in the snapshot
        rows.append(FieldRow(name, label, name, _kind_for_model_field(model_field)))
    return rows


def _json_summary(value: Any) -> str:
    """Return a one-line description of a dict or list, for the table column."""
    if isinstance(value, dict):
        keys = list(value)
        shown = ", ".join(keys[:4]) + (", …" if len(keys) > 4 else "")
        return f"{len(keys)} key{'s' if len(keys) != 1 else ''}: {shown}" if keys else "empty object"
    return f"{len(value)} item{'s' if len(value) != 1 else ''}" if value else "empty list"


def _display_python(raw: Any) -> DisplayValue:
    if raw is None or raw == "":
        return DisplayValue(KIND_SCALAR, text="", data=None)
    if isinstance(raw, models.Model):
        try:
            url = raw.get_absolute_url()
        except (AttributeError, NoReverseMatch):  # models without a detail view
            url = None
        return DisplayValue(KIND_OBJECT, text=str(raw), url=url, data=str(raw))
    if isinstance(raw, (dict, list)):
        return DisplayValue(KIND_JSON, text=_json_summary(raw), data=raw)
    return DisplayValue(KIND_SCALAR, text=str(raw), data=raw)


def current_value(obj, row: FieldRow) -> DisplayValue:
    """Return the live value of ``row`` on ``obj``, prepared for display."""
    if row.kind == KIND_UNTRACKED:
        return DisplayValue(KIND_UNTRACKED)
    if row.name.startswith(CUSTOM_FIELD_PREFIX):
        custom_fields = getattr(obj, "cf", None) or {}
        return _display_python(custom_fields.get(row.name[len(CUSTOM_FIELD_PREFIX) :]))
    raw = getattr(obj, row.name, None)
    if row.kind == KIND_LIST:
        items = list(raw.all()) if hasattr(raw, "all") else list(raw or [])
        return DisplayValue(KIND_LIST, items=[_display_python(item) for item in items], data=[str(i) for i in items])
    return _display_python(raw)


def _is_related(value: Any) -> bool:
    return isinstance(value, dict) and "id" in value


def display_snapshot(value: Any) -> DisplayValue:
    """Prepare a value taken from a changelog snapshot for display.

    Related objects appear in snapshots as dicts with ``id`` and usually ``display``; they are shown by name
    without a link, since the snapshot only carries the REST URL and the object may since have been deleted.
    """
    if value is None or value == "":
        return DisplayValue(KIND_SCALAR, text="", data=None)
    if _is_related(value):
        text = str(value.get("display") or value.get("name") or value["id"])
        return DisplayValue(KIND_OBJECT, text=text, data=text)
    if isinstance(value, list) and value and all(_is_related(item) for item in value):
        items = [display_snapshot(item) for item in value]
        return DisplayValue(KIND_LIST, items=items, data=[item.text for item in items])
    if isinstance(value, (dict, list)):
        return DisplayValue(KIND_JSON, text=_json_summary(value), data=value)
    return DisplayValue(KIND_SCALAR, text=str(value), data=value)


@lru_cache(maxsize=1)
def provenance_models() -> tuple[type, ...]:
    """Return every concrete change-logged model that has an edit form, in app registry order."""
    found = []
    for model in apps.get_models():
        if not issubclass(model, ChangeLoggedModel) or model._meta.abstract:
            continue
        try:
            has_form = get_form_for_model(model) is not None
        except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught  # a broken third-party forms module must not take the tab down
            logger.debug("Could not load a form for %s; skipping provenance", model, exc_info=True)
            has_form = False
        if has_form:
            found.append(model)
    return tuple(found)


def resolve_model(app_label: str, model_name: str) -> type:
    """Return the provenance-enabled model for ``app_label``/``model_name`` or raise Http404."""
    for model in provenance_models():
        if model._meta.app_label == app_label and model._meta.model_name == model_name:
            return model
    raise Http404(f"{app_label}.{model_name} does not support provenance")
