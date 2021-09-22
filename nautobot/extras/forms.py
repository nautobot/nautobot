from django import forms
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import TextField
from django.urls.base import reverse
from django.core.validators import ValidationError
from django.utils.safestring import mark_safe

from nautobot.dcim.models import DeviceRole, DeviceType, Platform, Region, Site
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.forms import (
    add_blank_choice,
    APISelectMultiple,
    BootstrapMixin,
    BulkEditForm,
    BulkEditNullBooleanSelect,
    ColorSelect,
    CSVModelChoiceField,
    CSVModelForm,
    CSVMultipleContentTypeField,
    DateTimePicker,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    JSONField,
    MultipleContentTypeField,
    SlugField,
    StaticSelect2,
    StaticSelect2Multiple,
    BOOLEAN_WITH_BLANK_CHOICES,
)
from nautobot.virtualization.models import Cluster, ClusterGroup
from .choices import *
from .datasources import get_datasource_content_choices
from .models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomLink,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    JobResult,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    Status,
    Tag,
    Webhook,
)
from .utils import FeatureQuery


#
# Custom fields
#


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

        # Add all applicable CustomFields to the form
        custom_fields = CustomField.objects.filter(content_types=self.obj_type).exclude(
            filter_logic=CustomFieldFilterLogicChoices.FILTER_DISABLED
        )
        for cf in custom_fields:
            field_name = "cf_{}".format(cf.name)
            self.fields[field_name] = cf.to_form_field(set_initial=True, enforce_required=False)


#
# Relationship
#


class RelationshipForm(BootstrapMixin, forms.ModelForm):

    slug = SlugField()
    source_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()).order_by("app_label", "model")
    )
    source_filter = JSONField(
        required=False,
        help_text='Enter any filters for the source object in <a href="https://json.org/">JSON</a> format.',
    )
    destination_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()).order_by("app_label", "model")
    )
    destination_filter = JSONField(
        required=False,
        help_text='Enter any filters for the destination object in <a href="https://json.org/">JSON</a> format.',
    )

    class Meta:
        model = Relationship
        fields = [
            "name",
            "slug",
            "description",
            "type",
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
                # cr_relationship-slug__destination since it's used to pick the destination object(s).
                # Conversely if we're on the "destination" side, the field will be cr_relationship-slug__source.
                field_name = f"cr_{relationship.slug}__{peer_side}"
                self.fields[field_name] = relationship.to_form_field(side=side)

                # if the object already exists, populate the field with existing values
                if self.instance.present_in_database:
                    if relationship.has_many(peer_side):
                        initial = [getattr(association, peer_side) for association in queryset.all()]
                        self.fields[field_name].initial = initial
                    else:
                        association = queryset.first()
                        if association:
                            self.fields[field_name].initial = getattr(association, peer_side)

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
                # If this side of the relationship is a "MANY" relation,
                # we can coexist with other existing RelationshipAssociations and there's nothing to check now.
                if relationship.has_many(side):
                    continue

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
                    existing_peer_associations = RelationshipAssociation.objects.filter(
                        relationship=relationship,
                        **{
                            f"{peer_side}_id": target_peer.pk,
                        },
                    ).exclude(**{f"{side}_id": self.instance.pk})
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
                f"{side}_type": self.obj_type,
                f"{side}_id": self.instance.pk,
            }
            existing_associations = RelationshipAssociation.objects.filter(**filters)

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
                    if peer_id == getattr(association, f"{peer_side}_id"):
                        # This association already exists, so we can ignore it
                        target_peer_ids.remove(peer_id)
                        break
                else:
                    # This association is not in target_peer_ids, so delete it
                    association.delete()

            # Anything remaining in target_peer_ids now does not exist yet and needs to be created.
            for peer_id in target_peer_ids:
                relationship = self.fields[field_name].model
                association = RelationshipAssociation(
                    relationship=relationship,
                    **{
                        f"{side}_type": self.obj_type,
                        f"{side}_id": self.instance.pk,
                        f"{peer_side}_type": getattr(relationship, f"{peer_side}_type"),
                        f"{peer_side}_id": peer_id,
                    },
                )

                association.clean()
                association.save()

    def save(self, commit=True):

        obj = super().save(commit)
        if commit:
            self._save_relationships()

        return obj


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
# Tags
#


class TagForm(BootstrapMixin, CustomFieldModelForm, RelationshipModelForm):
    slug = SlugField()

    class Meta:
        model = Tag
        fields = ["name", "slug", "color", "description"]


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


class TagBulkEditForm(BootstrapMixin, CustomFieldBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), widget=forms.MultipleHiddenInput)
    color = forms.CharField(max_length=6, required=False, widget=ColorSelect())
    description = forms.CharField(max_length=200, required=False)

    class Meta:
        nullable_fields = ["description"]


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
    tags = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)
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
    )

    username = forms.CharField(required=False, label="Username", help_text="Username for token authentication.")

    provided_contents = forms.MultipleChoiceField(
        required=False,
        label="Provides",
        choices=get_git_datasource_content_choices,
    )

    tags = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)

    class Meta:
        model = GitRepository
        fields = [
            "name",
            "slug",
            "remote_url",
            "branch",
            "_token",
            "username",
            "provided_contents",
            "tags",
        ]


class GitRepositoryCSVForm(CSVModelForm):
    class Meta:
        model = GitRepository
        fields = GitRepository.csv_headers


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
    )
    username = forms.CharField(
        required=False,
        label="Username",
    )

    class Meta:
        model = GitRepository


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
# Change logging
#


class ObjectChangeFilterForm(BootstrapMixin, forms.Form):
    model = ObjectChange
    q = forms.CharField(required=False, label="Search")
    time_after = forms.DateTimeField(label="After", required=False, widget=DateTimePicker())
    time_before = forms.DateTimeField(label="Before", required=False, widget=DateTimePicker())
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
# Jobs
#


class JobForm(BootstrapMixin, forms.Form):
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


class JobResultFilterForm(BootstrapMixin, forms.Form):
    model = JobResult
    q = forms.CharField(required=False, label="Search")
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


class ExportTemplateForm(BootstrapMixin, forms.ModelForm):
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("export_templates").get_query()).order_by(
            "app_label", "model"
        ),
        required=False,
        label="Content Types",
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
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("export_templates").get_query()).order_by(
            "app_label", "model"
        ),
        required=False,
        label="Content Types",
    )


class CustomLinkForm(BootstrapMixin, forms.ModelForm):
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_links").get_query()).order_by("app_label", "model"),
        required=False,
        label="Content Types",
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
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_links").get_query()).order_by("app_label", "model"),
        required=False,
        label="Content Types",
    )


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


#
# Statuses
#


class StatusForm(BootstrapMixin, CustomFieldModelForm, RelationshipModelForm):
    """Generic create/update form for `Status` objects."""

    slug = SlugField()
    content_types = MultipleContentTypeField(feature="statuses", label="Content Type(s)")

    class Meta:
        model = Status
        widgets = {"color": ColorSelect()}
        fields = ["name", "slug", "description", "content_types", "color"]


class StatusCSVForm(CustomFieldModelCSVForm):
    """Generic CSV bulk import form for `Status` objects."""

    slug = SlugField()
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


# Computed Fields


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
        )


class ComputedFieldFilterForm(BootstrapMixin, forms.Form):
    model = ComputedField
    q = forms.CharField(required=False, label="Search")
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()).order_by("app_label", "model"),
        required=False,
        label="Content Type",
    )
