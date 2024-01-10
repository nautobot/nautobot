from django import forms
from django.contrib.contenttypes.models import ContentType

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
            "comments",
            "tags",
        ]


class ContactBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Contact.objects.all(), widget=forms.MultipleHiddenInput())

    class Meta:
        model = Contact


class ContactFilterForm(NautobotFilterForm):
    model = Contact
    q = forms.CharField(required=False, label="Search")


class ObjectNewContactForm(NautobotModelForm):
    teams = DynamicModelMultipleChoiceField(
        queryset=Team.objects.all(),
        required=False,
        label="Team(s)",
    )
    associated_object_type = DynamicModelChoiceField(queryset=ContentType.objects.all(), required=True)
    associated_object_id = forms.CharField(required=True)
    role = DynamicModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        query_params={"content_types": ContactAssociation._meta.label_lower},
    )
    status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        required=True,
        query_params={"content_types": ContactAssociation._meta.label_lower},
    )

    class Meta:
        model = Contact
        fields = [
            "name",
            "phone",
            "email",
            "address",
            "teams",
            "comments",
            "associated_object_type",
            "associated_object_id",
            "role",
            "status",
        ]


class ObjectNewTeamForm(NautobotModelForm):
    contacts = DynamicModelMultipleChoiceField(
        queryset=Team.objects.all(),
        required=False,
        label="Team(s)",
    )
    associated_object_type = DynamicModelChoiceField(queryset=ContentType.objects.all(), required=True)
    associated_object_id = forms.CharField(required=True)
    role = DynamicModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        query_params={"content_types": ContactAssociation._meta.label_lower},
    )
    status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        required=True,
        query_params={"content_types": ContactAssociation._meta.label_lower},
    )

    class Meta:
        model = Team
        fields = [
            "name",
            "phone",
            "email",
            "address",
            "contacts",
            "comments",
            "associated_object_type",
            "associated_object_id",
            "role",
            "status",
        ]


class ContactAssociationForm(NautobotModelForm):
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
            "comments",
            "tags",
        ]


class TeamBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Team.objects.all(), widget=forms.MultipleHiddenInput())

    class Meta:
        model = Team


class TeamFilterForm(NautobotFilterForm):
    model = Team
    q = forms.CharField(required=False, label="Search")
