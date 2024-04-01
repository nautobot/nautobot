from django import forms
from django.contrib.contenttypes.models import ContentType

from nautobot.core.forms import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from nautobot.extras.models import Role, Status
from nautobot.extras.models.contacts import Contact, ContactAssociation, Team

from .base import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm
from .mixins import TagsBulkEditFormMixin


class ContactForm(NautobotModelForm):
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

    def __init__(self, instance=None, initial=None, **kwargs):
        if instance is not None:
            if initial is None:
                initial = {}
            initial.setdefault("teams", instance.teams.all())
        super().__init__(instance=instance, initial=initial, **kwargs)

    def save(self, *args, **kwargs):
        """
        Since `teams` field on Contact Model is the reverse side of an M2M,
        we have to override save() method to explictly set the teams for the Contact instance.
        """
        teams = self.cleaned_data.get("teams", [])
        obj = super().save(*args, **kwargs)
        obj.teams.set(teams)
        return obj


class ContactBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Contact.objects.all(), widget=forms.MultipleHiddenInput())
    phone = forms.CharField(required=False)
    email = forms.CharField(required=False)
    address = forms.CharField(required=False, widget=forms.Textarea())

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
        required=True,
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
            "tags",
            "associated_object_type",
            "associated_object_id",
            "role",
            "status",
        ]

    def save(self, *args, **kwargs):
        """
        Since `teams` field on Contact Model is the reverse side of an M2M,
        we have to override save() method to explictly set the teams for the Contact instance.
        """
        teams = self.cleaned_data.get("teams", [])
        obj = super().save(*args, **kwargs)
        obj.teams.set(teams)
        return obj


class ObjectNewTeamForm(NautobotModelForm):
    contacts = DynamicModelMultipleChoiceField(
        queryset=Contact.objects.all(),
        required=False,
        label="Contact(s)",
    )
    associated_object_type = DynamicModelChoiceField(queryset=ContentType.objects.all(), required=True)
    associated_object_id = forms.CharField(required=True)
    role = DynamicModelChoiceField(
        queryset=Role.objects.all(),
        required=True,
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
            "tags",
            "associated_object_type",
            "associated_object_id",
            "role",
            "status",
        ]


class ContactAssociationForm(NautobotModelForm):
    contact = DynamicModelChoiceField(queryset=Contact.objects.all(), required=False)
    team = DynamicModelChoiceField(queryset=Team.objects.all(), required=False)

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


class ContactAssociationBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ContactAssociation.objects.all(), widget=forms.MultipleHiddenInput())
    role = DynamicModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        query_params={"content_types": ContactAssociation._meta.label_lower},
    )
    status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        required=False,
        query_params={"content_types": ContactAssociation._meta.label_lower},
    )

    class Meta:
        model = ContactAssociation


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
    phone = forms.CharField(required=False)
    email = forms.CharField(required=False)
    address = forms.CharField(required=False, widget=forms.Textarea())

    class Meta:
        model = Team


class TeamFilterForm(NautobotFilterForm):
    model = Team
    q = forms.CharField(required=False, label="Search")
