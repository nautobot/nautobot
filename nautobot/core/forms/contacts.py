from django import forms

from nautobot.core.models.contacts import Contact, Team
from nautobot.extras.forms import (
    NautobotBulkEditForm,
    NautobotModelForm,
    RoleModelBulkEditFormMixin,
    TagsBulkEditFormMixin,
)


class ContactForm(NautobotModelForm):
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
