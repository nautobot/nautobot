"""Bulk lock / release forms for the Object Lock bulk actions."""

from django import forms

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import BootstrapMixin, DateTimePicker, StaticSelect2
from nautobot.extras.choices import ObjectLockModeChoices


class ObjectLockBulkLockForm(BootstrapMixin, forms.Form):
    """Collect lock parameters when bulk-locking selected objects."""

    mode = forms.ChoiceField(
        choices=ObjectLockModeChoices,
        widget=StaticSelect2(),
        label="Lock mode",
        help_text="Delete-locked, update-locked, or both.",
    )
    reason = forms.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Human-readable justification recorded on every claim.",
    )
    expires = forms.DateTimeField(
        required=True,  # UI-created locks MUST carry an expiry.
        widget=DateTimePicker(),
        label="Expires",
        help_text="Required. The lock is automatically released after this time.",
    )
    source_key = forms.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        label="Source key",
        help_text="Stable owner identifier used to release this batch later.",
    )


class ObjectLockBulkReleaseForm(BootstrapMixin, forms.Form):
    """Confirmation form for bulk-releasing claims; release itself takes no extra input."""
