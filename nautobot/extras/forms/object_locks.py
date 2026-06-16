"""Forms for the minimal Object Lock management view."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from nautobot.core.forms import (
    APISelectMultiple,
    BOOLEAN_WITH_BLANK_CHOICES,
    CSVContentTypeField,
    DynamicModelMultipleChoiceField,
    StaticSelect2,
)
from nautobot.extras.forms.base import NautobotFilterForm
from nautobot.extras.models import ObjectLock


class ObjectLockFilterForm(NautobotFilterForm):
    """Filter form for the Object Lock list view.

    Exposes the high-value ObjectLockFilterSet fields so locks can be filtered by content type, mode,
    source, and creator. Expiry-range filtering remains available on the filterset (e.g.
    ``?expires__gte=...`` / ``?expires__lte=...``) via the REST API and URL; it is not rendered as a
    sidebar field because ``NautobotFilterForm`` feeds multi-value data and a single datetime input
    cannot accept a list.
    """

    model = ObjectLock
    field_order = [
        "q",
        "content_type",
        "prevent_delete",
        "prevent_update",
        "source_key",
        "created_by",
    ]
    q = forms.CharField(required=False, label="Search")
    content_type = CSVContentTypeField(
        queryset=ContentType.objects.order_by("app_label", "model"),
        required=False,
        label="Content type",
    )
    prevent_delete = forms.NullBooleanField(
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    prevent_update = forms.NullBooleanField(
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    source_key = forms.CharField(required=False, label="Source")
    created_by = DynamicModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label="Created by",
        widget=APISelectMultiple(api_url="/api/users/users/"),
    )
