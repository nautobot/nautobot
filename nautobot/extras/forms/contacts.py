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
    name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={"placeholder": "Name"}))
    phone = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"placeholder": "Phone"}))
    email = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"placeholder": "E-mail"}))
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"placeholder": "Address"}))
    teams = DynamicModelMultipleChoiceField(
        queryset=Team.objects.all(),
        required=False,
        label="Team(s)",
    )
    contacts = DynamicModelMultipleChoiceField(
        queryset=Contact.objects.all(),
        required=False,
        label="Contact(s)",
    )
    contact_role = DynamicModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        label="Contact Role",
        query_params={"content_types": Contact._meta.label_lower},
    )
    team_role = DynamicModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        label="Team Role",
        query_params={"content_types": Team._meta.label_lower},
    )
    contact_association_role = DynamicModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        label="Role",
        query_params={"content_types": ContactAssociation._meta.label_lower},
    )
    team_association_role = DynamicModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        label="Role",
        query_params={"content_types": ContactAssociation._meta.label_lower},
    )
    contact_association_status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        required=True,
        label="Status",
        query_params={"content_types": ContactAssociation._meta.label_lower},
    )
    team_association_status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        required=True,
        label="Status",
        query_params={"content_types": ContactAssociation._meta.label_lower},
    )
    comments = forms.CharField(required=False, widget=forms.Textarea(attrs={"placeholder": "Comments"}))
    contact = DynamicModelChoiceField(queryset=Contact.objects.all(), required=False)
    team = DynamicModelChoiceField(queryset=Team.objects.all(), required=False)

    class Meta:
        model = ContactAssociation
        fields = [
            "name",
            "phone",
            "email",
            "address",
            "teams",
            "contacts",
            "contact_role",
            "contact_association_role",
            "team_association_role",
            "contact_association_status",
            "team_association_status",
            "comments",
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
