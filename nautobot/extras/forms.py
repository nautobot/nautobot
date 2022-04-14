from django import forms
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.fields import TextField
from django.forms import ModelMultipleChoiceField, inlineformset_factory
from django.urls.base import reverse
from django.utils.safestring import mark_safe

from nautobot.dcim.models import DeviceRole, DeviceType, Platform, Region, Site
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.forms import (
    add_blank_choice,
    APISelect,
    APISelectMultiple,
    BootstrapMixin,
    BulkEditForm,
    BulkEditNullBooleanSelect,
    ColorSelect,
    CSVContentTypeField,
    CSVModelChoiceField,
    CSVModelForm,
    CSVMultipleChoiceField,
    CSVMultipleContentTypeField,
    DateTimePicker,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    JSONField,
    MultipleContentTypeField,
    SlugField,
    StaticSelect2,
    StaticSelect2Multiple,
    TagFilterField,
)
from nautobot.utilities.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.virtualization.models import Cluster, ClusterGroup
from .choices import (
    CustomFieldFilterLogicChoices,
    JobExecutionType,
    JobResultStatusChoices,
    ObjectChangeActionChoices,
    RelationshipSideChoices,
    RelationshipTypeChoices,
)
from .constants import JOB_OVERRIDABLE_FIELDS
from .datasources import get_datasource_content_choices
from .models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    DynamicGroup,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobResult,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    Webhook,
)
from .registry import registry
from .utils import FeatureQuery, TaggableClassesQuery


#
# Form mixins
#


class RelationshipModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):

        self.obj_type = ContentType.objects.get_for_model(self._meta.model)
        self.relationships = []

        super().__init__(*args, **kwargs)

        self._append_relationships()

    def _append_relationships(self):
        """
        Append form fields for all Relationships assigned to this model.
        One form field per side will be added to the list.
        """
        for side, relationships in self.instance.get_relationships().items():
            for relationship, queryset in relationships.items():
                peer_side = RelationshipSideChoices.OPPOSITE[side]
                # If this model is on the "source" side of the relationship, then the field will be named
                # cr_<relationship-slug>__destination since it's used to pick the destination object(s).
                # If we're on the "destination" side, the field will be cr_<relationship-slug>__source.
                # For a symmetric relationship, both sides are "peer", so the field will be cr_<relationship-slug>__peer
                field_name = f"cr_{relationship.slug}__{peer_side}"
                self.fields[field_name] = relationship.to_form_field(side=side)

                # if the object already exists, populate the field with existing values
                if self.instance.present_in_database:
                    if relationship.has_many(peer_side):
                        initial = [association.get_peer(self.instance) for association in queryset.all()]
                        self.fields[field_name].initial = initial
                    else:
                        association = queryset.first()
                        if association:
                            self.fields[field_name].initial = association.get_peer(self.instance)

                # Annotate the field in the list of Relationship form fields
                self.relationships.append(field_name)

    def clean(self):
        """
        Verify that any requested RelationshipAssociations do not violate relationship cardinality restrictions.

        - For TYPE_ONE_TO_MANY and TYPE_ONE_TO_ONE relations, if the form's object is on the "source" side of
          the relationship, verify that the requested "destination" object(s) do not already have any existing
          RelationshipAssociation to a different source object.
        - For TYPE_ONE_TO_ONE relations, if the form's object is on the "destination" side of the relationship,
          verify that the requested "source" object does not have an existing RelationshipAssociation to
          a different destination object.
        """
        for side, relationships in self.instance.get_relationships().items():
            for relationship in relationships:
                # The form field name reflects what it provides, i.e. the peer object(s) to link via this relationship.
                peer_side = RelationshipSideChoices.OPPOSITE[side]
                field_name = f"cr_{relationship.slug}__{peer_side}"

                # Is the form trying to set this field (create/update a RelationshipAssociation(s))?
                # If not (that is, clearing the field / deleting RelationshipAssociation(s)), we don't need to check.
                if field_name not in self.cleaned_data or not self.cleaned_data[field_name]:
                    continue

                # Are any of the objects we want a relationship with already entangled with another object?
                if relationship.has_many(peer_side):
                    target_peers = [item for item in self.cleaned_data[field_name]]
                else:
                    target_peers = [self.cleaned_data[field_name]]

                for target_peer in target_peers:
                    if target_peer.pk == self.instance.pk:
                        raise ValidationError(
                            {field_name: f"Object {self.instance} cannot form a relationship to itself!"}
                        )

                    if relationship.has_many(side):
                        # No need to check for existing RelationshipAssociations since this is a "many" relationship
                        continue

                    if not relationship.symmetric:
                        existing_peer_associations = RelationshipAssociation.objects.filter(
                            relationship=relationship,
                            **{
                                f"{peer_side}_id": target_peer.pk,
                            },
                        ).exclude(**{f"{side}_id": self.instance.pk})
                    else:
                        existing_peer_associations = RelationshipAssociation.objects.filter(
                            (
                                (Q(source_id=target_peer.pk) & ~Q(destination_id=self.instance.pk))
                                | (Q(destination_id=target_peer.pk) & ~Q(source_id=self.instance.pk))
                            ),
                            relationship=relationship,
                        )

                    if existing_peer_associations.exists():
                        raise ValidationError(
                            {field_name: f"{target_peer} is already involved in a {relationship} relationship"}
                        )

        super().clean()

    def _save_relationships(self):
        """Update RelationshipAssociations for all Relationships on form save."""

        for field_name in self.relationships:
            # The field name tells us the side of the relationship that it is providing peer objects(s) to link into.
            peer_side = field_name.split("__")[-1]
            # Based on the side of the relationship that our local object represents,
            # find the list of existing RelationshipAssociations it already has for this Relationship.
            side = RelationshipSideChoices.OPPOSITE[peer_side]
            filters = {
                "relationship": self.fields[field_name].model,
            }
            if side != RelationshipSideChoices.SIDE_PEER:
                filters.update({f"{side}_type": self.obj_type, f"{side}_id": self.instance.pk})
                existing_associations = RelationshipAssociation.objects.filter(**filters)
            else:
                existing_associations = RelationshipAssociation.objects.filter(
                    (
                        Q(source_type=self.obj_type, source_id=self.instance.pk)
                        | Q(destination_type=self.obj_type, destination_id=self.instance.pk)
                    ),
                    **filters,
                )

            # Get the list of target peer ids (PKs) that are specified in the form
            target_peer_ids = []
            if hasattr(self.cleaned_data[field_name], "__iter__"):
                # One-to-many or many-to-many association
                target_peer_ids = [item.pk for item in self.cleaned_data[field_name]]
            elif self.cleaned_data[field_name]:
                # Many-to-one or one-to-one association
                target_peer_ids = [self.cleaned_data[field_name].pk]
            else:
                # Unset/delete case
                target_peer_ids = []

            # Create/delete RelationshipAssociations as needed to match the target_peer_ids list

            # First, for each existing association, if it's one that's already in target_peer_ids,
            # we can discard it from target_peer_ids (no update needed to this association).
            # Conversely, if it's *not* in target_peer_ids, we should delete it.
            for association in existing_associations:
                for peer_id in target_peer_ids:
                    if peer_side != RelationshipSideChoices.SIDE_PEER:
                        if peer_id == getattr(association, f"{peer_side}_id"):
                            # This association already exists, so we can ignore it
                            target_peer_ids.remove(peer_id)
                            break
                    else:
                        if peer_id == association.source_id or peer_id == association.destination_id:
                            # This association already exists, so we can ignore it
                            target_peer_ids.remove(peer_id)
                            break
                else:
                    # This association is not in target_peer_ids, so delete it
                    association.delete()

            # Anything remaining in target_peer_ids now does not exist yet and needs to be created.
            for peer_id in target_peer_ids:
                relationship = self.fields[field_name].model
                if not relationship.symmetric:
                    association = RelationshipAssociation(
                        relationship=relationship,
                        **{
                            f"{side}_type": self.obj_type,
                            f"{side}_id": self.instance.pk,
                            f"{peer_side}_type": getattr(relationship, f"{peer_side}_type"),
                            f"{peer_side}_id": peer_id,
                        },
                    )
                else:
                    # Symmetric association - source/destination are interchangeable
                    association = RelationshipAssociation(
                        relationship=relationship,
                        source_type=self.obj_type,
                        source_id=self.instance.pk,
                        destination_type=self.obj_type,  # since this is a symmetric relationship this is OK
                        destination_id=peer_id,
                    )

                association.clean()
                association.save()

    def save(self, commit=True):

        obj = super().save(commit)
        if commit:
            self._save_relationships()

        return obj


#
# Computed Fields
#


class ComputedFieldForm(BootstrapMixin, forms.ModelForm):

    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()).order_by("app_label", "model"),
        required=True,
        label="Content Type",
    )
    slug = SlugField(slug_source="label")

    class Meta:
        model = ComputedField
        fields = (
            "content_type",
            "label",
            "slug",
            "description",
            "template",
            "fallback_value",
            "weight",
            "advanced_ui",
        )


class ComputedFieldFilterForm(BootstrapMixin, forms.Form):
    model = ComputedField
    q = forms.CharField(required=False, label="Search")
    content_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()).order_by("app_label", "model"),
        required=False,
        label="Content Type",
    )


#
# Config contexts
#


class ConfigContextForm(BootstrapMixin, forms.ModelForm):
    regions = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), required=False)
    sites = DynamicModelMultipleChoiceField(queryset=Site.objects.all(), required=False)
    roles = DynamicModelMultipleChoiceField(queryset=DeviceRole.objects.all(), required=False)
    device_types = DynamicModelMultipleChoiceField(queryset=DeviceType.objects.all(), required=False)
    platforms = DynamicModelMultipleChoiceField(queryset=Platform.objects.all(), required=False)
    cluster_groups = DynamicModelMultipleChoiceField(queryset=ClusterGroup.objects.all(), required=False)
    clusters = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), required=False)
    tenant_groups = DynamicModelMultipleChoiceField(queryset=TenantGroup.objects.all(), required=False)
    tenants = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), required=False)

    data = JSONField(label="")

    class Meta:
        model = ConfigContext
        fields = (
            "name",
            "weight",
            "description",
            "schema",
            "is_active",
            "regions",
            "sites",
            "roles",
            "device_types",
            "platforms",
            "cluster_groups",
            "clusters",
            "tenant_groups",
            "tenants",
            "tags",
            "data",
        )


class ConfigContextBulkEditForm(BootstrapMixin, BulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ConfigContext.objects.all(), widget=forms.MultipleHiddenInput)
    schema = DynamicModelChoiceField(queryset=ConfigContextSchema.objects.all(), required=False)
    weight = forms.IntegerField(required=False, min_value=0)
    is_active = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect())
    description = forms.CharField(required=False, max_length=100)

    class Meta:
        nullable_fields = [
            "description",
            "schema",
        ]


class ConfigContextFilterForm(BootstrapMixin, forms.Form):
    q = forms.CharField(required=False, label="Search")
    # FIXME(glenn) filtering by owner_content_type
    schema = DynamicModelChoiceField(queryset=ConfigContextSchema.objects.all(), to_field_name="slug", required=False)
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    site = DynamicModelMultipleChoiceField(queryset=Site.objects.all(), to_field_name="slug", required=False)
    role = DynamicModelMultipleChoiceField(queryset=DeviceRole.objects.all(), to_field_name="slug", required=False)
    type = DynamicModelMultipleChoiceField(queryset=DeviceType.objects.all(), to_field_name="slug", required=False)
    platform = DynamicModelMultipleChoiceField(queryset=Platform.objects.all(), to_field_name="slug", required=False)
    cluster_group = DynamicModelMultipleChoiceField(
        queryset=ClusterGroup.objects.all(), to_field_name="slug", required=False
    )
    cluster_id = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), required=False, label="Cluster")
    tenant_group = DynamicModelMultipleChoiceField(
        queryset=TenantGroup.objects.all(), to_field_name="slug", required=False
    )
    tenant = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), to_field_name="slug", required=False)
    tag = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), to_field_name="slug", required=False)


#
# Filter form for local config context data
#


class LocalContextFilterForm(forms.Form):
    local_context_data = forms.NullBooleanField(
        required=False,
        label="Has local config context data",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    local_context_schema = DynamicModelMultipleChoiceField(
        queryset=ConfigContextSchema.objects.all(), to_field_name="slug", required=False
    )


#
# Model form for local config context data
#


class LocalContextModelForm(forms.ModelForm):
    local_context_schema = DynamicModelChoiceField(queryset=ConfigContextSchema.objects.all(), required=False)
    local_context_data = JSONField(required=False, label="")


class LocalContextModelBulkEditForm(BulkEditForm):
    local_context_schema = DynamicModelChoiceField(queryset=ConfigContextSchema.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # append nullable fields
        self.nullable_fields.append("local_context_schema")


#
# Config context schemas
#


class ConfigContextSchemaForm(BootstrapMixin, forms.ModelForm):
    data_schema = JSONField(label="")
    slug = SlugField()

    class Meta:
        model = ConfigContextSchema
        fields = (
            "name",
            "slug",
            "description",
            "data_schema",
        )


class ConfigContextSchemaBulkEditForm(BootstrapMixin, BulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ConfigContextSchema.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(required=False, max_length=100)

    class Meta:
        nullable_fields = [
            "description",
        ]


class ConfigContextSchemaFilterForm(BootstrapMixin, forms.Form):
    q = forms.CharField(required=False, label="Search")
    # FIXME(glenn) filtering by owner_content_type


#
# Custom fields
#


# CustomFieldChoice inline formset for use with providing dynamic rows when creating/editing choices
# for `CustomField` objects in UI views. Fields/exclude must be set but since we're using all the
# fields we're just setting `exclude=()` here.
CustomFieldChoiceFormSet = inlineformset_factory(
    parent_model=CustomField,
    model=CustomFieldChoice,
    exclude=(),
    extra=5,
    widgets={
        "value": forms.TextInput(attrs={"class": "form-control"}),
        "weight": forms.NumberInput(attrs={"class": "form-control"}),
    },
)


class CustomFieldForm(BootstrapMixin, forms.ModelForm):
    # TODO: Migrate custom field model from name to slug #464
    # Once that's done we can set "name" as a proper (Auto)SlugField,
    # but for the moment, that field only works with fields specifically named "slug"
    description = forms.CharField(
        required=False,
        help_text="Also used as the help text when editing models using this custom field.<br>"
        '<a href="https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet" target="_blank">'
        "Markdown</a> syntax is supported.",
    )
    content_types = MultipleContentTypeField(
        feature="custom_fields", help_text="The object(s) to which this field applies."
    )

    class Meta:
        model = CustomField
        fields = (
            "content_types",
            "type",
            "label",
            "name",
            "description",
            "required",
            "advanced_ui",
            "filter_logic",
            "default",
            "weight",
            "validation_minimum",
            "validation_maximum",
            "validation_regex",
        )


class CustomFieldModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):

        self.obj_type = ContentType.objects.get_for_model(self._meta.model)
        self.custom_fields = []

        super().__init__(*args, **kwargs)

        self._append_customfield_fields()

    def _append_customfield_fields(self):
        """
        Append form fields for all CustomFields assigned to this model.
        """
        # Append form fields; assign initial values if modifying and existing object
        for cf in CustomField.objects.filter(content_types=self.obj_type):
            field_name = "cf_{}".format(cf.name)
            if self.instance.present_in_database:
                self.fields[field_name] = cf.to_form_field(set_initial=False)
                self.fields[field_name].initial = self.instance.cf.get(cf.name)
            else:
                self.fields[field_name] = cf.to_form_field()

            # Annotate the field in the list of CustomField form fields
            self.custom_fields.append(field_name)

    def clean(self):

        # Save custom field data on instance
        for cf_name in self.custom_fields:
            self.instance.cf[cf_name[3:]] = self.cleaned_data.get(cf_name)

        return super().clean()


class CustomFieldModelCSVForm(CSVModelForm, CustomFieldModelForm):
    def _append_customfield_fields(self):

        # Append form fields
        for cf in CustomField.objects.filter(content_types=self.obj_type):
            field_name = "cf_{}".format(cf.name)
            self.fields[field_name] = cf.to_form_field(for_csv_import=True)

            # Annotate the field in the list of CustomField form fields
            self.custom_fields.append(field_name)


class CustomFieldBulkEditForm(BulkEditForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.custom_fields = []
        self.obj_type = ContentType.objects.get_for_model(self.model)

        # Add all applicable CustomFields to the form
        custom_fields = CustomField.objects.filter(content_types=self.obj_type)
        for cf in custom_fields:
            name = self._get_field_name(cf.name)
            # Annotate non-required custom fields as nullable
            if not cf.required:
                self.nullable_fields.append(name)
            self.fields[name] = cf.to_form_field(set_initial=False, enforce_required=False)
            # Annotate this as a custom field
            self.custom_fields.append(name)

    @staticmethod
    def _get_field_name(name):
        # Return the desired field name
        return name


class CustomFieldBulkCreateForm(CustomFieldBulkEditForm):
    """
    Adaptation of CustomFieldBulkEditForm which uses prefixed field names
    """

    @staticmethod
    def _get_field_name(name):
        # Return a prefixed version of the name
        return "cf_{}".format(name)


class CustomFieldFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):

        self.obj_type = ContentType.objects.get_for_model(self.model)

        super().__init__(*args, **kwargs)

        custom_fields = CustomField.objects.filter(content_types=self.obj_type).exclude(
            filter_logic=CustomFieldFilterLogicChoices.FILTER_DISABLED
        )
        for cf in custom_fields:
            field_name = "cf_{}".format(cf.name)
            if cf.type == "json":
                self.fields[field_name] = cf.to_form_field(
                    set_initial=True, enforce_required=False, simple_json_filter=True
                )
            else:
                self.fields[field_name] = cf.to_form_field(set_initial=True, enforce_required=False)


#
# Nautobot base form for use in most new custom model forms.
#


class NautobotModelForm(BootstrapMixin, CustomFieldModelForm, RelationshipModelForm):
    """
    This class exists to combine common functionality and is used to inherit from throughout the
    codebase where all three of BootstrapMixin, CustomFieldModelForm and RelationshipModelForm are
    needed.
    """


#
# Custom Links
#


class CustomLinkForm(BootstrapMixin, forms.ModelForm):
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_links").get_query()).order_by("app_label", "model"),
        label="Content Type",
    )

    class Meta:
        model = CustomLink
        fields = (
            "content_type",
            "name",
            "text",
            "target_url",
            "weight",
            "group_name",
            "button_class",
            "new_window",
        )


class CustomLinkFilterForm(BootstrapMixin, forms.Form):
    model = CustomLink
    q = forms.CharField(required=False, label="Search")
    content_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_links").get_query()).order_by("app_label", "model"),
        required=False,
        label="Content Type",
    )


#
# Dynamic Groups
#


class DynamicGroupForm(NautobotModelForm):
    """DynamicGroup model form."""

    slug = SlugField()
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("dynamic_groups").get_query()).order_by("app_label", "model"),
        label="Content Type",
    )

    class Meta:
        model = DynamicGroup
        fields = [
            "name",
            "slug",
            "description",
            "content_type",
        ]


class DynamicGroupFilterForm(BootstrapMixin, forms.Form):
    """DynamicGroup filter form."""

    model = DynamicGroup
    q = forms.CharField(required=False, label="Search")
    content_type = MultipleContentTypeField(feature="dynamic_groups", choices_as_strings=True, label="Content Type")


#
# Export Templates
#


class ExportTemplateForm(BootstrapMixin, forms.ModelForm):
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("export_templates").get_query()).order_by(
            "app_label", "model"
        ),
        label="Content Type",
    )

    class Meta:
        model = ExportTemplate
        fields = (
            "content_type",
            "name",
            "description",
            "template_code",
            "mime_type",
            "file_extension",
        )


class ExportTemplateFilterForm(BootstrapMixin, forms.Form):
    model = ExportTemplate
    q = forms.CharField(required=False, label="Search")
    content_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("export_templates").get_query()).order_by(
            "app_label", "model"
        ),
        required=False,
        label="Content Type",
    )


#
# Git repositories and other data sources
#


def get_git_datasource_content_choices():
    return get_datasource_content_choices("extras.gitrepository")


class PasswordInputWithPlaceholder(forms.PasswordInput):
    """PasswordInput that is populated with a placeholder value if any existing value is present."""

    def __init__(self, attrs=None, placeholder="", render_value=False):
        if placeholder:
            render_value = True
        self._placeholder = placeholder
        super().__init__(attrs=attrs, render_value=render_value)

    def get_context(self, name, value, attrs):
        if value:
            value = self._placeholder
        return super().get_context(name, value, attrs)


class GitRepositoryForm(BootstrapMixin, RelationshipModelForm):

    slug = SlugField(help_text="Filesystem-friendly unique shorthand")

    remote_url = forms.URLField(
        required=True,
        label="Remote URL",
        help_text="Only http:// and https:// URLs are presently supported",
    )

    _token = forms.CharField(
        required=False,
        label="Token",
        widget=PasswordInputWithPlaceholder(placeholder=GitRepository.TOKEN_PLACEHOLDER),
        help_text="<em>Deprecated</em> - use a secrets group instead.",
    )

    username = forms.CharField(
        required=False,
        label="Username",
        help_text="Username for token authentication.<br><em>Deprecated</em> - use a secrets group instead",
    )

    secrets_group = DynamicModelChoiceField(required=False, queryset=SecretsGroup.objects.all())

    provided_contents = forms.MultipleChoiceField(
        required=False,
        label="Provides",
        choices=get_git_datasource_content_choices,
    )

    class Meta:
        model = GitRepository
        fields = [
            "name",
            "slug",
            "remote_url",
            "branch",
            "username",
            "_token",
            "secrets_group",
            "provided_contents",
            "tags",
        ]

    def clean(self):
        super().clean()

        # set dryrun after a successful clean
        if "_dryrun_create" in self.data or "_dryrun_update" in self.data:
            self.instance.set_dryrun()


class GitRepositoryCSVForm(CSVModelForm):
    secrets_group = CSVModelChoiceField(
        queryset=SecretsGroup.objects.all(),
        to_field_name="name",
        required=False,
        help_text="Secrets group for repository access (if any)",
    )

    class Meta:
        model = GitRepository
        fields = GitRepository.csv_headers

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["provided_contents"] = CSVMultipleChoiceField(
            choices=get_git_datasource_content_choices(),
            required=False,
            help_text=mark_safe(
                "The data types this repository provides. Multiple values must be comma-separated and wrapped in "
                'double quotes (e.g. <code>"extras.job,extras.configcontext"</code>).'
            ),
        )


class GitRepositoryBulkEditForm(BootstrapMixin, BulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=GitRepository.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    remote_url = forms.CharField(
        label="Remote URL",
        required=False,
    )
    branch = forms.CharField(
        required=False,
    )
    _token = forms.CharField(
        required=False,
        label="Token",
        widget=PasswordInputWithPlaceholder(placeholder=GitRepository.TOKEN_PLACEHOLDER),
        help_text="<em>Deprecated</em> - use a secrets group instead.",
    )
    username = forms.CharField(
        required=False,
        label="Username",
        help_text="<em>Deprecated</em> - use a secrets group instead.",
    )

    secrets_group = DynamicModelChoiceField(required=False, queryset=SecretsGroup.objects.all())

    class Meta:
        model = GitRepository
        nullable_fields = ["secrets_group"]


#
# GraphQL saved queries
#


class GraphQLQueryForm(BootstrapMixin, forms.ModelForm):
    slug = SlugField()
    query = TextField()

    class Meta:
        model = GraphQLQuery
        fields = (
            "name",
            "slug",
            "query",
        )

    def get_action_url(self):
        return reverse("extras:graphqlquery_add")


class GraphQLQueryFilterForm(BootstrapMixin, forms.Form):
    model = GraphQLQuery
    q = forms.CharField(required=False, label="Search")


#
# Image attachments
#


class ImageAttachmentForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ImageAttachment
        fields = [
            "name",
            "image",
        ]


#
# Jobs
#


class JobForm(BootstrapMixin, forms.Form):
    """
    This form is used to render the user input fields for a Job class. Its fields are dynamically
    controlled by the job definition. See `nautobot.extras.jobs.BaseJob.as_form`
    """

    _commit = forms.BooleanField(
        required=False,
        initial=True,
        label="Commit changes",
        help_text="Commit changes to the database (uncheck for a dry-run)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Move _commit to the end of the form
        commit = self.fields.pop("_commit")
        self.fields["_commit"] = commit

    @property
    def requires_input(self):
        """
        A boolean indicating whether the form requires user input (ignore the _commit field).
        """
        return bool(len(self.fields) > 1)


class JobEditForm(NautobotModelForm):
    slug = SlugField()

    class Meta:
        model = Job
        fields = [
            "slug",
            "enabled",
            "name_override",
            "name",
            "grouping_override",
            "grouping",
            "description_override",
            "description",
            "commit_default_override",
            "commit_default",
            "hidden_override",
            "hidden",
            "read_only_override",
            "read_only",
            "approval_required_override",
            "approval_required",
            "soft_time_limit_override",
            "soft_time_limit",
            "time_limit_override",
            "time_limit",
            "tags",
        ]

    def clean(self):
        """
        For all overridable fields, if they aren't marked as overridden, revert them to the underlying value if known.
        """
        cleaned_data = super().clean() or self.cleaned_data
        job_class = self.instance.job_class
        if job_class is not None:
            for field_name in JOB_OVERRIDABLE_FIELDS:
                if not cleaned_data.get(f"{field_name}_override", False):
                    cleaned_data[field_name] = getattr(job_class, field_name)
        return cleaned_data


class JobFilterForm(BootstrapMixin, forms.Form):
    model = Job
    q = forms.CharField(required=False, label="Search")
    installed = forms.NullBooleanField(
        initial=True,
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    enabled = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    commit_default = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    hidden = forms.NullBooleanField(
        initial=False,
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    read_only = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    approval_required = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    tag = TagFilterField(model)


class JobScheduleForm(BootstrapMixin, forms.Form):
    """
    This form is rendered alongside the JobForm but deals specifically with the fields needed to either
    execute the job immediately, or schedule it for later. Each field name is prefixed with an underscore
    because in the POST body, they share a namespace with the JobForm which includes fields defined by the
    job author, so the underscore prefix helps to avoid name collisions.
    """

    _schedule_type = forms.ChoiceField(
        choices=JobExecutionType,
        help_text="The job can either run immediately, once in the future, or on a recurring schedule.",
        label="Type",
    )
    _schedule_name = forms.CharField(
        required=False,
        label="Schedule name",
        help_text="Name for the job schedule.",
    )
    _schedule_start_time = forms.DateTimeField(
        required=False,
        label="Starting date and time",
        widget=DateTimePicker(),
    )

    def clean(self):
        """
        Validate all required information is present if the job needs to be scheduled
        """
        cleaned_data = super().clean()

        if "_schedule_type" in cleaned_data and cleaned_data.get("_schedule_type") != JobExecutionType.TYPE_IMMEDIATELY:
            if not cleaned_data.get("_schedule_name"):
                raise ValidationError({"_schedule_name": "Please provide a name for the job schedule."})

            if (
                not cleaned_data.get("_schedule_start_time")
                or cleaned_data.get("_schedule_start_time") < ScheduledJob.earliest_possible_time()
            ):
                raise ValidationError(
                    {
                        "_schedule_start_time": "Please enter a valid date and time greater than or equal to the current date and time."
                    }
                )


class JobResultFilterForm(BootstrapMixin, forms.Form):
    model = JobResult
    q = forms.CharField(required=False, label="Search")
    job_model = DynamicModelMultipleChoiceField(
        label="Job",
        queryset=Job.objects.all(),
        required=False,
        to_field_name="slug",
        widget=APISelectMultiple(api_url="/api/extras/jobs/", api_version="1.3"),
    )
    # FIXME(glenn) Filtering by obj_type?
    name = forms.CharField(required=False)
    user = DynamicModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label="User",
        widget=APISelectMultiple(
            api_url="/api/users/users/",
        ),
    )
    status = forms.ChoiceField(
        choices=add_blank_choice(JobResultStatusChoices),
        required=False,
        widget=StaticSelect2(),
    )


class ScheduledJobFilterForm(BootstrapMixin, forms.Form):
    model = ScheduledJob
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False)
    job_model = DynamicModelMultipleChoiceField(
        label="Job",
        queryset=Job.objects.all(),
        required=False,
        to_field_name="slug",
        widget=APISelectMultiple(api_url="/api/extras/job-models/"),
    )
    total_run_count = forms.IntegerField(required=False)


#
# Change logging
#


class ObjectChangeFilterForm(BootstrapMixin, forms.Form):
    model = ObjectChange
    q = forms.CharField(required=False, label="Search")
    time__gte = forms.DateTimeField(label="After", required=False, widget=DateTimePicker())
    time__lte = forms.DateTimeField(label="Before", required=False, widget=DateTimePicker())
    action = forms.ChoiceField(
        choices=add_blank_choice(ObjectChangeActionChoices),
        required=False,
        widget=StaticSelect2(),
    )
    user_id = DynamicModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label="User",
        widget=APISelectMultiple(
            api_url="/api/users/users/",
        ),
    )
    changed_object_type_id = DynamicModelMultipleChoiceField(
        queryset=ContentType.objects.all(),
        required=False,
        label="Object Type",
        widget=APISelectMultiple(
            api_url="/api/extras/content-types/",
        ),
    )


#
# Relationship
#


class RelationshipForm(BootstrapMixin, forms.ModelForm):

    slug = SlugField()
    source_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()).order_by("app_label", "model"),
        help_text="The source object type to which this relationship applies.",
    )
    source_filter = JSONField(
        required=False,
        help_text="Queryset filter matching the applicable source objects of the selected type.<br>"
        'Enter in <a href="https://json.org/">JSON</a> format.',
    )
    destination_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()).order_by("app_label", "model"),
        help_text="The destination object type to which this relationship applies.",
    )
    destination_filter = JSONField(
        required=False,
        help_text="Queryset filter matching the applicable destination objects of the selected type.<br>"
        'Enter in <a href="https://json.org/">JSON</a> format.',
    )

    class Meta:
        model = Relationship
        fields = [
            "name",
            "slug",
            "description",
            "type",
            "advanced_ui",
            "source_type",
            "source_label",
            "source_hidden",
            "source_filter",
            "destination_type",
            "destination_label",
            "destination_hidden",
            "destination_filter",
        ]

    def save(self, commit=True):

        # TODO add support for owner when a CR is created in the UI
        obj = super().save(commit)

        return obj


class RelationshipFilterForm(BootstrapMixin, forms.Form):
    model = Relationship

    type = forms.MultipleChoiceField(choices=RelationshipTypeChoices, required=False, widget=StaticSelect2Multiple())

    source_type = MultipleContentTypeField(
        feature="relationships", choices_as_strings=True, required=False, label="Source Type"
    )

    destination_type = MultipleContentTypeField(
        feature="relationships", choices_as_strings=True, required=False, label="Destination Type"
    )


class RelationshipAssociationFilterForm(BootstrapMixin, forms.Form):
    model = RelationshipAssociation

    relationship = DynamicModelMultipleChoiceField(
        queryset=Relationship.objects.all(),
        to_field_name="slug",
        required=False,
    )

    source_type = MultipleContentTypeField(
        feature="relationships", choices_as_strings=True, required=False, label="Source Type"
    )

    destination_type = MultipleContentTypeField(
        feature="relationships", choices_as_strings=True, required=False, label="Destination Type"
    )


#
# Secrets
#


def provider_choices():
    return sorted([(slug, provider.name) for slug, provider in registry["secrets_providers"].items()])


class SecretForm(NautobotModelForm):
    """Create/update form for `Secret` objects."""

    slug = SlugField()

    provider = forms.ChoiceField(choices=provider_choices, widget=StaticSelect2())

    parameters = JSONField(help_text='Enter parameters in <a href="https://json.org/">JSON</a> format.')

    class Meta:
        model = Secret
        fields = [
            "name",
            "slug",
            "description",
            "provider",
            "parameters",
            "tags",
        ]


class SecretCSVForm(CustomFieldModelCSVForm):
    class Meta:
        model = Secret
        fields = Secret.csv_headers


def provider_choices_with_blank():
    return add_blank_choice(sorted([(slug, provider.name) for slug, provider in registry["secrets_providers"].items()]))


class SecretFilterForm(BootstrapMixin, CustomFieldFilterForm):
    model = Secret
    q = forms.CharField(required=False, label="Search")
    provider = forms.MultipleChoiceField(
        choices=provider_choices_with_blank, widget=StaticSelect2Multiple(), required=False
    )
    tag = TagFilterField(model)


# Inline formset for use with providing dynamic rows when creating/editing assignments of Secrets to SecretsGroups.
SecretsGroupAssociationFormSet = inlineformset_factory(
    parent_model=SecretsGroup,
    model=SecretsGroupAssociation,
    fields=("access_type", "secret_type", "secret"),
    extra=5,
    widgets={
        "access_type": StaticSelect2,
        "secret_type": StaticSelect2,
        "secret": APISelect(api_url="/api/extras/secrets/"),
    },
)


class SecretsGroupForm(NautobotModelForm):
    """Create/update form for `SecretsGroup` objects."""

    slug = SlugField()

    class Meta:
        model = SecretsGroup
        fields = [
            "name",
            "slug",
            "description",
        ]


class SecretsGroupFilterForm(BootstrapMixin, CustomFieldFilterForm):
    model = SecretsGroup
    q = forms.CharField(required=False, label="Search")


#
# Statuses
#


class StatusForm(NautobotModelForm):
    """Generic create/update form for `Status` objects."""

    slug = SlugField()
    content_types = MultipleContentTypeField(feature="statuses", label="Content Type(s)")

    class Meta:
        model = Status
        widgets = {"color": ColorSelect()}
        fields = ["name", "slug", "description", "content_types", "color"]


class StatusCSVForm(CustomFieldModelCSVForm):
    """Generic CSV bulk import form for `Status` objects."""

    content_types = CSVMultipleContentTypeField(
        feature="statuses",
        choices_as_strings=True,
        help_text=mark_safe(
            "The object types to which this status applies. Multiple values "
            "must be comma-separated and wrapped in double quotes. (e.g. "
            '<code>"dcim.device,dcim.rack"</code>)'
        ),
        label="Content type(s)",
    )

    class Meta:
        model = Status
        fields = Status.csv_headers
        help_texts = {
            "color": mark_safe("RGB color in hexadecimal (e.g. <code>00ff00</code>)"),
        }


class StatusFilterForm(BootstrapMixin, CustomFieldFilterForm):
    """Filtering/search form for `Status` objects."""

    model = Status
    q = forms.CharField(required=False, label="Search")
    content_types = MultipleContentTypeField(
        feature="statuses", choices_as_strings=True, required=False, label="Content Type(s)"
    )
    color = forms.CharField(max_length=6, required=False, widget=ColorSelect())


class StatusBulkEditForm(BootstrapMixin, CustomFieldBulkEditForm):
    """Bulk edit/delete form for `Status` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=Status.objects.all(), widget=forms.MultipleHiddenInput)
    color = forms.CharField(max_length=6, required=False, widget=ColorSelect())
    content_types = MultipleContentTypeField(feature="statuses", required=False, label="Content Type(s)")

    class Meta:
        nullable_fields = []


class StatusBulkEditFormMixin(forms.Form):
    """Mixin to add non-required `status` choice field to forms."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"] = DynamicModelChoiceField(
            required=False,
            queryset=Status.objects.all(),
            query_params={"content_types": self.model._meta.label_lower},
        )
        self.order_fields(self.field_order)  # Reorder fields again


class StatusFilterFormMixin(forms.Form):
    """
    Mixin to add non-required `status` multiple-choice field to filter forms.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"] = DynamicModelMultipleChoiceField(
            required=False,
            queryset=Status.objects.all(),
            query_params={"content_types": self.model._meta.label_lower},
            to_field_name="slug",
        )
        self.order_fields(self.field_order)  # Reorder fields again


class StatusModelCSVFormMixin(CSVModelForm):
    """Mixin to add a required `status` choice field to CSV import forms."""

    status = CSVModelChoiceField(
        queryset=Status.objects.all(),
        to_field_name="slug",
        help_text="Operational status",
    )


#
# Tags
#


class TagForm(NautobotModelForm):
    slug = SlugField()
    content_types = ModelMultipleChoiceField(
        label="Content Type(s)",
        queryset=TaggableClassesQuery().as_queryset,
    )

    class Meta:
        model = Tag
        fields = ["name", "slug", "color", "description", "content_types"]

    def clean(self):
        data = super().clean()

        if self.instance.present_in_database:
            # check if tag is assigned to any of the removed content_types
            content_types_id = [content_type.id for content_type in self.cleaned_data["content_types"]]
            errors = self.instance.validate_content_types_removal(content_types_id)

            if errors:
                raise ValidationError(errors)

        return data


class TagCSVForm(CustomFieldModelCSVForm):
    slug = SlugField()

    class Meta:
        model = Tag
        fields = Tag.csv_headers
        help_texts = {
            "color": mark_safe("RGB color in hexadecimal (e.g. <code>00ff00</code>)"),
        }


class AddRemoveTagsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add add/remove tags fields
        self.fields["add_tags"] = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)
        self.fields["remove_tags"] = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)


class TagFilterForm(BootstrapMixin, CustomFieldFilterForm):
    model = Tag
    q = forms.CharField(required=False, label="Search")
    content_types = MultipleContentTypeField(
        choices_as_strings=True,
        required=False,
        label="Content Type(s)",
        queryset=TaggableClassesQuery().as_queryset,
    )


class TagBulkEditForm(BootstrapMixin, CustomFieldBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), widget=forms.MultipleHiddenInput)
    color = forms.CharField(max_length=6, required=False, widget=ColorSelect())
    description = forms.CharField(max_length=200, required=False)

    class Meta:
        nullable_fields = ["description"]


#
# Webhooks
#


class WebhookForm(BootstrapMixin, forms.ModelForm):
    content_types = MultipleContentTypeField(feature="webhooks", required=False, label="Content Type(s)")

    class Meta:
        model = Webhook
        fields = (
            "name",
            "content_types",
            "enabled",
            "type_create",
            "type_update",
            "type_delete",
            "payload_url",
            "http_method",
            "http_content_type",
            "additional_headers",
            "body_template",
            "secret",
            "ssl_verification",
            "ca_file_path",
        )

    def clean(self):
        data = super().clean()

        conflicts = Webhook.check_for_conflicts(
            instance=self.instance,
            content_types=self.cleaned_data.get("content_types"),
            payload_url=self.cleaned_data.get("payload_url"),
            type_create=self.cleaned_data.get("type_create"),
            type_update=self.cleaned_data.get("type_update"),
            type_delete=self.cleaned_data.get("type_delete"),
        )

        if conflicts:
            raise ValidationError(conflicts)

        return data


class WebhookFilterForm(BootstrapMixin, forms.Form):
    model = Webhook
    q = forms.CharField(required=False, label="Search")
    content_types = MultipleContentTypeField(
        feature="webhooks", choices_as_strings=True, required=False, label="Content Type(s)"
    )
    type_create = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    type_update = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    type_delete = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    enabled = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
