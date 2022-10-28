from datetime import datetime
import json
from collections import OrderedDict

from db_file_storage.model_utils import delete_file, delete_file_if_needed
from db_file_storage.storage import DatabaseFileStorage
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpResponse
from django.utils.text import slugify
from django.urls import reverse
from graphene_django.settings import graphene_settings
from graphql import get_default_backend
from graphql.error import GraphQLSyntaxError
from graphql.language.ast import OperationDefinition
from jsonschema import draft7_format_checker
from jsonschema.exceptions import SchemaError, ValidationError as JSONSchemaValidationError
from jsonschema.validators import Draft7Validator
from rest_framework.utils.encoders import JSONEncoder

from nautobot.core.fields import AutoSlugField
from nautobot.core.models import BaseModel
from nautobot.core.models.generics import OrganizationalModel
from nautobot.extras.choices import (
    CustomLinkButtonClassChoices,
    WebhookHttpMethodChoices,
)
from nautobot.extras.constants import HTTP_CONTENT_TYPE_JSON
from nautobot.extras.models import ChangeLoggedModel
from nautobot.extras.models.mixins import NotesMixin
from nautobot.extras.models.relationships import RelationshipModel
from nautobot.extras.querysets import ConfigContextQuerySet, NotesQuerySet
from nautobot.extras.utils import extras_features, FeatureQuery, image_upload
from nautobot.utilities.utils import deepmerge, render_jinja2

# Avoid breaking backward compatibility on anything that might expect these to still be defined here:
from .jobs import JOB_LOGS, Job, JobLogEntry, JobResult, ScheduledJob, ScheduledJobs  # noqa: F401


#
# Config contexts
#


class ConfigContextSchemaValidationMixin:
    """
    Mixin that provides validation of config context data against a json schema.
    """

    def _validate_with_schema(self, data_field, schema_field):
        schema = getattr(self, schema_field)
        data = getattr(self, data_field)

        # If schema is None, then no schema has been specified on the instance and thus no validation should occur.
        if schema:
            try:
                Draft7Validator(schema.data_schema, format_checker=draft7_format_checker).validate(data)
            except JSONSchemaValidationError as e:
                raise ValidationError({data_field: [f"Validation using the JSON Schema {schema} failed.", e.message]})


@extras_features("graphql")
class ConfigContext(BaseModel, ChangeLoggedModel, ConfigContextSchemaValidationMixin, NotesMixin):
    """
    A ConfigContext represents a set of arbitrary data available to any Device or VirtualMachine matching its assigned
    qualifiers (region, site, etc.). For example, the data stored in a ConfigContext assigned to site A and tenant B
    will be available to a Device in site A assigned to tenant B. Data is stored in JSON format.
    """

    name = models.CharField(max_length=100, db_index=True)

    # A ConfigContext *may* be owned by another model, such as a GitRepository, or it may be un-owned
    owner_content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=FeatureQuery("config_context_owners"),
        default=None,
        null=True,
        blank=True,
    )
    owner_object_id = models.UUIDField(default=None, null=True, blank=True)
    owner = GenericForeignKey(
        ct_field="owner_content_type",
        fk_field="owner_object_id",
    )

    weight = models.PositiveSmallIntegerField(default=1000)
    description = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(
        default=True,
    )
    schema = models.ForeignKey(
        to="extras.ConfigContextSchema",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Optional schema to validate the structure of the data",
    )
    regions = models.ManyToManyField(to="dcim.Region", related_name="+", blank=True)
    sites = models.ManyToManyField(to="dcim.Site", related_name="+", blank=True)
    locations = models.ManyToManyField(to="dcim.Location", related_name="+", blank=True)
    roles = models.ManyToManyField(to="dcim.DeviceRole", related_name="+", blank=True)
    device_types = models.ManyToManyField(to="dcim.DeviceType", related_name="+", blank=True)
    device_redundancy_groups = models.ManyToManyField(to="dcim.DeviceRedundancyGroup", related_name="+", blank=True)
    platforms = models.ManyToManyField(to="dcim.Platform", related_name="+", blank=True)
    cluster_groups = models.ManyToManyField(to="virtualization.ClusterGroup", related_name="+", blank=True)
    clusters = models.ManyToManyField(to="virtualization.Cluster", related_name="+", blank=True)
    tenant_groups = models.ManyToManyField(to="tenancy.TenantGroup", related_name="+", blank=True)
    tenants = models.ManyToManyField(to="tenancy.Tenant", related_name="+", blank=True)
    tags = models.ManyToManyField(to="extras.Tag", related_name="+", blank=True)
    data = models.JSONField(encoder=DjangoJSONEncoder)

    objects = ConfigContextQuerySet.as_manager()

    class Meta:
        ordering = ["weight", "name"]
        unique_together = [["name", "owner_content_type", "owner_object_id"]]

    def __str__(self):
        if self.owner:
            return f"[{self.owner}] {self.name}"
        return self.name

    def get_absolute_url(self):
        return reverse("extras:configcontext", kwargs={"pk": self.pk})

    def clean(self):
        super().clean()

        # Verify that JSON data is provided as an object
        if not isinstance(self.data, dict):
            raise ValidationError({"data": 'JSON data must be in object form. Example: {"foo": 123}'})

        # Validate data against schema
        self._validate_with_schema("data", "schema")

        # Check for a duplicated `name`. This is necessary because Django does not consider two NULL fields to be equal,
        # and thus if the `owner` is NULL, a duplicate `name` will not otherwise automatically raise an exception.
        if (
            ConfigContext.objects.exclude(pk=self.pk)
            .filter(name=self.name, owner_content_type=self.owner_content_type, owner_object_id=self.owner_object_id)
            .exists()
        ):
            raise ValidationError({"name": "A ConfigContext with this name already exists."})


class ConfigContextModel(models.Model, ConfigContextSchemaValidationMixin):
    """
    A model which includes local configuration context data. This local data will override any inherited data from
    ConfigContexts.
    """

    local_context_data = models.JSONField(
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
    )
    local_context_schema = models.ForeignKey(
        to="extras.ConfigContextSchema",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Optional schema to validate the structure of the data",
    )
    # The local context data *may* be owned by another model, such as a GitRepository, or it may be un-owned
    local_context_data_owner_content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=FeatureQuery("config_context_owners"),
        default=None,
        null=True,
        blank=True,
    )
    local_context_data_owner_object_id = models.UUIDField(default=None, null=True, blank=True)
    local_context_data_owner = GenericForeignKey(
        ct_field="local_context_data_owner_content_type",
        fk_field="local_context_data_owner_object_id",
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=("local_context_data_owner_content_type", "local_context_data_owner_object_id")),
        ]

    def get_config_context(self):
        """
        Return the rendered configuration context for a device or VM.
        """

        if not hasattr(self, "config_context_data"):
            # Annotation not available, so fall back to manually querying for the config context
            config_context_data = ConfigContext.objects.get_for_object(self).values_list("data", flat=True)
        else:
            config_context_data = self.config_context_data or []
            # Annotation has keys "weight" and "name" (used for ordering) and "data" (the actual config context data)
            config_context_data = [
                c["data"] for c in sorted(config_context_data, key=lambda k: (k["weight"], k["name"]))
            ]

        # Compile all config data, overwriting lower-weight values with higher-weight values where a collision occurs
        data = OrderedDict()
        for context in config_context_data:
            data = deepmerge(data, context)

        # If the object has local config context data defined, merge it last
        if self.local_context_data:
            data = deepmerge(data, self.local_context_data)

        return data

    def clean(self):
        super().clean()

        # Verify that JSON data is provided as an object
        if self.local_context_data and not isinstance(self.local_context_data, dict):
            raise ValidationError({"local_context_data": 'JSON data must be in object form. Example: {"foo": 123}'})

        if self.local_context_schema and not self.local_context_data:
            raise ValidationError({"local_context_schema": "Local context data must exist for a schema to be applied."})

        # Validate data against schema
        self._validate_with_schema("local_context_data", "local_context_schema")


@extras_features(
    "custom_fields",
    "custom_validators",
    "graphql",
    "relationships",
)
class ConfigContextSchema(OrganizationalModel):
    """
    This model stores jsonschema documents where are used to optionally validate config context data payloads.
    """

    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200, blank=True)
    slug = AutoSlugField(populate_from="name", max_length=200, unique=None, db_index=True)
    data_schema = models.JSONField(
        help_text="A JSON Schema document which is used to validate a config context object."
    )
    # A ConfigContextSchema *may* be owned by another model, such as a GitRepository, or it may be un-owned
    owner_content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=FeatureQuery("config_context_owners"),
        default=None,
        null=True,
        blank=True,
    )
    owner_object_id = models.UUIDField(default=None, null=True, blank=True)
    owner = GenericForeignKey(
        ct_field="owner_content_type",
        fk_field="owner_object_id",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name", "owner_content_type", "owner_object_id"], name="unique_name_owner"),
        ]

    def __str__(self):
        if self.owner:
            return f"[{self.owner}] {self.name}"
        return self.name

    def get_absolute_url(self):
        return reverse("extras:configcontextschema", args=[self.slug])

    def clean(self):
        """
        Validate the schema
        """
        super().clean()

        try:
            Draft7Validator.check_schema(self.data_schema)
        except SchemaError as e:
            raise ValidationError({"data_schema": e.message})

        if (
            not isinstance(self.data_schema, dict)
            or "properties" not in self.data_schema
            or self.data_schema.get("type") != "object"
        ):
            raise ValidationError(
                {
                    "data_schema": "Nautobot only supports context data in the form of an object and thus the "
                    "JSON schema must be of type object and specify a set of properties."
                }
            )


#
# Custom links
#


@extras_features("graphql")
class CustomLink(BaseModel, ChangeLoggedModel, NotesMixin):
    """
    A custom link to an external representation of a Nautobot object. The link text and URL fields accept Jinja2 template
    code to be rendered with an object as context.
    """

    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=FeatureQuery("custom_links"),
    )
    name = models.CharField(max_length=100, unique=True)
    text = models.CharField(
        max_length=500,
        help_text="Jinja2 template code for link text. Reference the object as <code>{{ obj }}</code> such as <code>{{ obj.platform.slug }}</code>. Links which render as empty text will not be displayed.",
    )
    target_url = models.CharField(
        max_length=500,
        verbose_name="URL",
        help_text="Jinja2 template code for link URL. Reference the object as <code>{{ obj }}</code> such as <code>{{ obj.platform.slug }}</code>.",
    )
    weight = models.PositiveSmallIntegerField(default=100)
    group_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Links with the same group will appear as a dropdown menu",
    )
    button_class = models.CharField(
        max_length=30,
        choices=CustomLinkButtonClassChoices,
        default=CustomLinkButtonClassChoices.CLASS_DEFAULT,
        help_text="The class of the first link in a group will be used for the dropdown button",
    )
    new_window = models.BooleanField(help_text="Force link to open in a new window")

    class Meta:
        ordering = ["group_name", "weight", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("extras:customlink", kwargs={"pk": self.pk})


#
# Export templates
#


@extras_features(
    "graphql",
    "relationships",
)
class ExportTemplate(BaseModel, ChangeLoggedModel, RelationshipModel, NotesMixin):
    # An ExportTemplate *may* be owned by another model, such as a GitRepository, or it may be un-owned
    owner_content_type = models.ForeignKey(
        to=ContentType,
        related_name="export_template_owners",
        on_delete=models.CASCADE,
        limit_choices_to=FeatureQuery("export_template_owners"),
        default=None,
        null=True,
        blank=True,
    )
    owner_object_id = models.UUIDField(default=None, null=True, blank=True)
    owner = GenericForeignKey(
        ct_field="owner_content_type",
        fk_field="owner_object_id",
    )
    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=FeatureQuery("export_templates"),
    )
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    template_code = models.TextField(
        help_text="The list of objects being exported is passed as a context variable named <code>queryset</code>."
    )
    mime_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="MIME type",
        help_text="Defaults to <code>text/plain</code>",
    )
    file_extension = models.CharField(
        max_length=15,
        blank=True,
        help_text="Extension to append to the rendered filename",
    )

    class Meta:
        ordering = ["content_type", "name"]
        unique_together = [["content_type", "name", "owner_content_type", "owner_object_id"]]

    def __str__(self):
        if self.owner:
            return f"[{self.owner}] {self.content_type}: {self.name}"
        return f"{self.content_type}: {self.name}"

    def render(self, queryset):
        """
        Render the contents of the template.
        """
        context = {"queryset": queryset}
        output = render_jinja2(self.template_code, context)

        # Replace CRLF-style line terminators
        output = output.replace("\r\n", "\n")

        return output

    def render_to_response(self, queryset):
        """
        Render the template to an HTTP response, delivered as a named file attachment
        """
        output = self.render(queryset)
        mime_type = "text/plain" if not self.mime_type else self.mime_type

        # Build the response
        response = HttpResponse(output, content_type=mime_type)
        extension = f".{self.file_extension}" if self.file_extension else ""
        filename = f"{settings.BRANDING_PREPENDED_FILENAME}{queryset.model._meta.verbose_name_plural}{extension}"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    def get_absolute_url(self):
        return reverse("extras:exporttemplate", kwargs={"pk": self.pk})

    def clean(self):
        super().clean()
        if self.file_extension.startswith("."):
            self.file_extension = self.file_extension[1:]

        # Don't allow two ExportTemplates with the same name, content_type, and owner.
        # This is necessary because Django doesn't consider NULL=NULL, and so if owner is NULL the unique_together
        # condition will never be matched even if name and content_type are the same.
        if (
            ExportTemplate.objects.exclude(pk=self.pk)
            .filter(
                name=self.name,
                content_type=self.content_type,
                owner_content_type=self.owner_content_type,
                owner_object_id=self.owner_object_id,
            )
            .exists()
        ):
            raise ValidationError({"name": "An ExportTemplate with this name and content type already exists."})


#
# File attachments
#


class FileAttachment(BaseModel):
    """An object for storing the contents and metadata of a file in the database.

    This object is used by `FileProxy` objects to retrieve file contents and is
    not intended to be used standalone.
    """

    bytes = models.BinaryField()
    filename = models.CharField(max_length=255)
    mimetype = models.CharField(max_length=255)

    def __str__(self):
        return self.filename

    class Meta:
        ordering = ["filename"]


def database_storage():
    """Returns storage backend used by `FileProxy.file` to store files in the database."""
    return DatabaseFileStorage()


class FileProxy(BaseModel):
    """An object to store a file in the database.

    The `file` field can be used like a file handle. The file contents are stored and retrieved from
    `FileAttachment` objects.

    The associated `FileAttachment` is removed when `delete()` is called. For this reason, one
    should never use bulk delete operations on `FileProxy` objects, unless `FileAttachment` objects
    are also bulk-deleted, because a model's `delete()` method is not called during bulk operations.
    In most cases, it is better to iterate over a queryset of `FileProxy` objects and call
    `delete()` on each one individually.
    """

    name = models.CharField(max_length=255)
    file = models.FileField(
        upload_to="extras.FileAttachment/bytes/filename/mimetype",
        storage=database_storage,  # Use only this backend
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        get_latest_by = "uploaded_at"
        ordering = ["name"]
        verbose_name_plural = "file proxies"

    def save(self, *args, **kwargs):
        delete_file_if_needed(self, "file")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        delete_file(self, "file")


#
# Saved GraphQL queries
#


@extras_features("graphql")
class GraphQLQuery(BaseModel, ChangeLoggedModel, NotesMixin):
    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    query = models.TextField()
    variables = models.JSONField(encoder=DjangoJSONEncoder, default=dict, blank=True)

    class Meta:
        ordering = ("slug",)
        verbose_name = "GraphQL query"
        verbose_name_plural = "GraphQL queries"

    def get_absolute_url(self):
        return reverse("extras:graphqlquery", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        variables = {}
        schema = graphene_settings.SCHEMA
        backend = get_default_backend()
        # Load query into GraphQL backend
        document = backend.document_from_string(schema, self.query)

        # Inspect the parsed document tree (document.document_ast) to retrieve the query (operation) definition(s)
        # that define one or more variables. For each operation and variable definition, store the variable's
        # default value (if any) into our own "variables" dict.
        definitions = [
            d
            for d in document.document_ast.definitions
            if isinstance(d, OperationDefinition) and d.variable_definitions
        ]
        for definition in definitions:
            for variable_definition in definition.variable_definitions:
                default = variable_definition.default_value.value if variable_definition.default_value else ""
                variables[variable_definition.variable.name.value] = default

        self.variables = variables
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        schema = graphene_settings.SCHEMA
        backend = get_default_backend()
        try:
            backend.document_from_string(schema, self.query)
        except GraphQLSyntaxError as error:
            raise ValidationError({"query": error})

    def __str__(self):
        return self.name


#
# Health Check
#


class HealthCheckTestModel(BaseModel):
    title = models.CharField(max_length=128)


#
# Image Attachments
#


class ImageAttachment(BaseModel):
    """
    An uploaded image which is associated with an object.
    """

    content_type = models.ForeignKey(to=ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField(db_index=True)
    parent = GenericForeignKey(ct_field="content_type", fk_field="object_id")
    image = models.ImageField(upload_to=image_upload, height_field="image_height", width_field="image_width")
    image_height = models.PositiveSmallIntegerField()
    image_width = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=50, blank=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)  # name may be non-unique

    def __str__(self):
        if self.name:
            return self.name
        filename = self.image.name.rsplit("/", 1)[-1]
        return filename.split("_", 2)[2]

    def delete(self, *args, **kwargs):

        _name = self.image.name

        super().delete(*args, **kwargs)

        # Delete file from disk
        self.image.delete(save=False)

        # Deleting the file erases its name. We restore the image's filename here in case we still need to reference it
        # before the request finishes. (For example, to display a message indicating the ImageAttachment was deleted.)
        self.image.name = _name

    @property
    def size(self):
        """
        Wrapper around `image.size` to suppress an OSError in case the file is inaccessible. Also opportunistically
        catch other exceptions that we know other storage back-ends to throw.
        """
        expected_exceptions = [OSError]

        try:
            from botocore.exceptions import ClientError

            expected_exceptions.append(ClientError)
        except ImportError:
            pass

        try:
            return self.image.size
        except tuple(expected_exceptions):
            return None


#
# Notes
#


@extras_features("graphql", "webhooks")
class Note(BaseModel, ChangeLoggedModel):
    """
    Notes allow anyone with proper permissions to add a note to an object.
    """

    assigned_object_type = models.ForeignKey(to=ContentType, on_delete=models.CASCADE)
    assigned_object_id = models.UUIDField(db_index=True)
    assigned_object = GenericForeignKey(ct_field="assigned_object_type", fk_field="assigned_object_id")
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="note",
        blank=True,
        null=True,
    )
    user_name = models.CharField(max_length=150, editable=False)

    slug = AutoSlugField(populate_from="assigned_object")
    note = models.TextField()
    objects = NotesQuerySet.as_manager()

    class Meta:
        ordering = ["created"]

    def slugify_function(self, content):
        return slugify(f"{str(content)[:50]}-{datetime.now().isoformat()}")

    def __str__(self):
        return str(self.slug)

    def save(self, *args, **kwargs):
        # Record the user's name as static strings
        self.user_name = self.user.username if self.user else "Undefined"
        return super().save(*args, **kwargs)


#
# Webhooks
#


@extras_features("graphql")
class Webhook(BaseModel, ChangeLoggedModel, NotesMixin):
    """
    A Webhook defines a request that will be sent to a remote application when an object is created, updated, and/or
    delete in Nautobot. The request will contain a representation of the object, which the remote application can act on.
    Each Webhook can be limited to firing only on certain actions or certain object types.
    """

    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="webhooks",
        verbose_name="Object types",
        limit_choices_to=FeatureQuery("webhooks"),
        help_text="The object(s) to which this Webhook applies.",
    )
    name = models.CharField(max_length=150, unique=True)
    type_create = models.BooleanField(default=False, help_text="Call this webhook when a matching object is created.")
    type_update = models.BooleanField(default=False, help_text="Call this webhook when a matching object is updated.")
    type_delete = models.BooleanField(default=False, help_text="Call this webhook when a matching object is deleted.")
    payload_url = models.CharField(
        max_length=500,
        verbose_name="URL",
        help_text="A POST will be sent to this URL when the webhook is called.",
    )
    enabled = models.BooleanField(default=True)
    http_method = models.CharField(
        max_length=30,
        choices=WebhookHttpMethodChoices,
        default=WebhookHttpMethodChoices.METHOD_POST,
        verbose_name="HTTP method",
    )
    http_content_type = models.CharField(
        max_length=100,
        default=HTTP_CONTENT_TYPE_JSON,
        verbose_name="HTTP content type",
        help_text="The complete list of official content types is available "
        '<a href="https://www.iana.org/assignments/media-types/media-types.xhtml">here</a>.',
    )
    additional_headers = models.TextField(
        blank=True,
        help_text="User-supplied HTTP headers to be sent with the request in addition to the HTTP content type. "
        "Headers should be defined in the format <code>Name: Value</code>. Jinja2 template processing is "
        "support with the same context as the request body (below).",
    )
    body_template = models.TextField(
        blank=True,
        help_text="Jinja2 template for a custom request body. If blank, a JSON object representing the change will be "
        "included. Available context data includes: <code>event</code>, <code>model</code>, "
        "<code>timestamp</code>, <code>username</code>, <code>request_id</code>, and <code>data</code>.",
    )
    secret = models.CharField(
        max_length=255,
        blank=True,
        help_text="When provided, the request will include a 'X-Hook-Signature' "
        "header containing a HMAC hex digest of the payload body using "
        "the secret as the key. The secret is not transmitted in "
        "the request.",
    )
    ssl_verification = models.BooleanField(
        default=True,
        verbose_name="SSL verification",
        help_text="Enable SSL certificate verification. Disable with caution!",
    )
    ca_file_path = models.CharField(
        max_length=4096,
        null=True,
        blank=True,
        verbose_name="CA File Path",
        help_text="The specific CA certificate file to use for SSL verification. "
        "Leave blank to use the system defaults.",
    )

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        # At least one action type must be selected
        if not self.type_create and not self.type_delete and not self.type_update:
            raise ValidationError("You must select at least one type: create, update, and/or delete.")

        # CA file path requires SSL verification enabled
        if not self.ssl_verification and self.ca_file_path:
            raise ValidationError(
                {"ca_file_path": "Do not specify a CA certificate file if SSL verification is disabled."}
            )

    def render_headers(self, context):
        """
        Render additional_headers and return a dict of Header: Value pairs.
        """
        if not self.additional_headers:
            return {}
        ret = {}
        data = render_jinja2(self.additional_headers, context)
        for line in data.splitlines():
            header, value = line.split(":")
            ret[header.strip()] = value.strip()
        return ret

    def render_body(self, context):
        """
        Render the body template, if defined. Otherwise, dump the context as a JSON object.
        """
        if self.body_template:
            return render_jinja2(self.body_template, context)
        else:
            return json.dumps(context, cls=JSONEncoder, ensure_ascii=False)

    def get_absolute_url(self):
        return reverse("extras:webhook", kwargs={"pk": self.pk})

    @classmethod
    def check_for_conflicts(
        cls, instance=None, content_types=None, payload_url=None, type_create=None, type_update=None, type_delete=None
    ):
        """
        Helper method for enforcing uniqueness.

        Don't allow two webhooks with the same content_type, same payload_url, and any action(s) in common.
        Called by WebhookForm.clean() and WebhookSerializer.validate()
        """

        conflicts = {}
        webhook_error_msg = "A webhook already exists for {action} on {content_type} to URL {url}"

        if instance is not None and instance.present_in_database:
            # This is a PATCH and might not include all relevant data e.g content_types, payload_url or actions
            # Therefore we get data not available from instance
            content_types = instance.content_types.all() if content_types is None else content_types
            payload_url = instance.payload_url if payload_url is None else payload_url
            type_create = instance.type_create if type_create is None else type_create
            type_update = instance.type_update if type_update is None else type_update
            type_delete = instance.type_delete if type_delete is None else type_delete

        if content_types is not None:
            for content_type in content_types:
                webhooks = cls.objects.filter(content_types__in=[content_type], payload_url=payload_url)
                if instance and instance.present_in_database:
                    webhooks = webhooks.exclude(pk=instance.pk)

                existing_type_create = webhooks.filter(type_create=type_create).exists() if type_create else False
                existing_type_update = webhooks.filter(type_update=type_update).exists() if type_update else False
                existing_type_delete = webhooks.filter(type_delete=type_delete).exists() if type_delete else False

                if existing_type_create:
                    conflicts.setdefault("type_create", []).append(
                        webhook_error_msg.format(content_type=content_type, action="create", url=payload_url),
                    )

                if existing_type_update:
                    conflicts.setdefault("type_update", []).append(
                        webhook_error_msg.format(content_type=content_type, action="update", url=payload_url),
                    )

                if existing_type_delete:
                    conflicts.setdefault("type_delete", []).append(
                        webhook_error_msg.format(content_type=content_type, action="delete", url=payload_url),
                    )

        return conflicts
