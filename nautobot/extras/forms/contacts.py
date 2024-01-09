from django import forms

from nautobot.core.forms import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from nautobot.extras.models.contacts import Contact, ContactAssociation, Team
from nautobot.extras.models import Role, Status

from .base import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm
from .mixins import RoleModelBulkEditFormMixin, TagsBulkEditFormMixin


class ContactForm(NautobotModelForm):
    # TODO: this doesn't work automatically since this is the reverse side of an M2M. Just gets ignored at present.
    teams = DynamicModelMultipleChoiceField(
        queryset=Team.objects.all(),
        required=False,
        label="Team(s)",
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


class ContactFilterForm(NautobotFilterForm):
    model = Contact
    q = forms.CharField(required=False, label="Search")


class ContactAssociationForm(NautobotModelForm):
    contact = DynamicModelChoiceField(queryset=Contact.objects.all(), required=False)
    team = DynamicModelChoiceField(queryset=Team.objects.all(), required=False)
    # associated_object_type = DynamicModelChoiceField(queryset=ContentType.objects.all())

    class Meta:
        model = ContactAssociation
        fields = [
            "contact",
            "team",
            "associated_object_type",
            "associated_object_id",
            "role",
            "status",
        ]


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


class TeamFilterForm(NautobotFilterForm):
    model = Team
    q = forms.CharField(required=False, label="Search")


class ContactAssociationFormSetForm(forms.ModelForm):
    """Form used for rows in the Contacts/Teams formset when editing related objects."""

    contact = DynamicModelChoiceField(queryset=Contact.objects.all(), required=False)
    team = DynamicModelChoiceField(queryset=Team.objects.all(), required=False)
    status = DynamicModelChoiceField(
        queryset=Status.objects.all(), required=True, query_params={"content_types": "extras.contactassociation"}
    )
    role = DynamicModelChoiceField(
        queryset=Role.objects.all(), required=False, query_params={"content_types": "extras.contactassociation"}
    )

    class Meta:
        model = ContactAssociation
        fields = ("contact", "team", "status", "role")
