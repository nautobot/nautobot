from django import forms

from nautobot.core.forms import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from nautobot.extras.models.contacts import Contact, Team

from .base import NautobotBulkEditForm, NautobotModelForm
from .mixins import RoleModelBulkEditFormMixin, TagsBulkEditFormMixin


class ContactForm(NautobotModelForm):
    teams = DynamicModelMultipleChoiceField(
        queryset=Team.objects.all(),
        required=False,
        label = "Team(s)",
    )
    class Meta:
        model = Contact
        fields = [
            "name",
            "phone",
            "email",
            "address",
            "teams",
            "role",
            "comments",
            "tags",
        ]


class ContactBulkEditForm(TagsBulkEditFormMixin, RoleModelBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Contact.objects.all(), widget=forms.MultipleHiddenInput())

    class Meta:
        model = Contact


class TeamForm(NautobotModelForm):
    contacts = DynamicModelMultipleChoiceField(
        queryset=Contact.objects.all(),
        required=False,
        label="Contact(s)",
    )
    class Meta:
        model = Team
        fields = [
            "name",
            "phone",
            "email",
            "address",
            "contacts",
            "role",
            "comments",
            "tags",
        ]


class TeamBulkEditForm(TagsBulkEditFormMixin, RoleModelBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Team.objects.all(), widget=forms.MultipleHiddenInput())

    class Meta:
        model = Team
