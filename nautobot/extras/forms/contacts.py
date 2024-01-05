from django import forms
from django.contrib.contenttypes.models import ContentType

from nautobot.core.forms import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from nautobot.extras.models.contacts import Contact, ContactAssociation, Team
from nautobot.extras.models import Role, Status

from .base import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm
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


class ContactFilterForm(NautobotFilterForm):
    model = Contact
    q = forms.CharField(required=False, label="Search")


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


class BaseInlineGFKFormSet(forms.BaseModelFormSet):
    """
    Like forms.BaseInlineFormSet, but for child objects related to a parent by GenericForeignKey rather than ForeignKey.
    """

    def __init__(self, data=None, files=None, instance=None, save_as_new=False, prefix=None, queryset=None, **kwargs):
        if instance is None:
            self.instance = self.ct_field.content_type.model()  # TODO
        else:
            self.instance = instance
        self.save_as_new = save_as_new
        if queryset is None:
            queryset = self.model._default_manager
        if self.instance.present_in_database:
            qs = queryset.filter(
                **{
                    self.ct_field.name: ContentType.objects.get_for_model(self.instance),
                    self.fk_field.name: self.instance.pk,
                }
            )
        else:
            qs = queryset.none()
        self.unique_fields = {self.ct_field.name, self.fk_field.name}
        super().__init__(data, files, prefix=prefix, queryset=qs, **kwargs)

        # TODO remainder of BaseInlineFormSet


def inline_gfk_formset_factory(
    parent_model,
    model,
    form=forms.ModelForm,
    formset=BaseInlineGFKFormSet,
    ct_field_name="associated_object_type",
    fk_field_name="associated_object_id",
    fields=None,
    exclude=None,
    extra=3,
    can_order=False,
    can_delete=True,
    max_num=None,
    formfield_callback=None,
    widgets=None,
    validate_max=False,
    localized_fields=None,
    labels=None,
    help_texts=None,
    error_messages=None,
    min_num=None,
    validate_min=False,
    field_classes=None,
    absolute_max=None,
    can_delete_extra=True,
):
    ct_field = [field for field in model._meta.fields if field.name == ct_field_name][0]
    fk_field = [field for field in model._meta.fields if field.name == fk_field_name][0]
    kwargs = {
        "form": form,
        "formfield_callback": formfield_callback,
        "formset": formset,
        "extra": extra,
        "can_delete": can_delete,
        "can_order": can_order,
        "fields": fields,
        "exclude": exclude,
        "min_num": min_num,
        "max_num": max_num,
        "widgets": widgets,
        "validate_min": validate_min,
        "validate_max": validate_max,
        "localized_fields": localized_fields,
        "labels": labels,
        "help_texts": help_texts,
        "error_messages": error_messages,
        "field_classes": field_classes,
        "absolute_max": absolute_max,
        "can_delete_extra": can_delete_extra,
    }
    FormSet = forms.modelformset_factory(model, **kwargs)
    FormSet.ct_field = ct_field
    FormSet.fk_field = fk_field
    return FormSet
