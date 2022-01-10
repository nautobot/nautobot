import json
import logging
import uuid
from collections import OrderedDict
from datetime import timedelta

from celery import schedules
from db_file_storage.model_utils import delete_file, delete_file_if_needed
from db_file_storage.storage import DatabaseFileStorage
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import signals
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django_celery_beat.clockedschedule import clocked
from django_celery_beat.managers import ExtendedManager
from graphene_django.settings import graphene_settings
from graphql import get_default_backend
from graphql.error import GraphQLSyntaxError
from graphql.language.ast import OperationDefinition
from jsonschema import draft7_format_checker
from jsonschema.exceptions import SchemaError, ValidationError as JSONSchemaValidationError
from jsonschema.validators import Draft7Validator
from rest_framework.utils.encoders import JSONEncoder

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.fields import AutoSlugField
from nautobot.core.models import BaseModel
from nautobot.core.models.generics import OrganizationalModel
from nautobot.extras.choices import (
    CustomLinkButtonClassChoices,
    LogLevelChoices,
    JobExecutionType,
    JobResultStatusChoices,
    WebhookHttpMethodChoices,
)
from nautobot.extras.constants import (
    HTTP_CONTENT_TYPE_JSON,
    JOB_LOG_MAX_ABSOLUTE_URL_LENGTH,
    JOB_LOG_MAX_GROUPING_LENGTH,
    JOB_LOG_MAX_LOG_OBJECT_LENGTH,
)
from nautobot.extras.models import ChangeLoggedModel
from nautobot.extras.models.customfields import CustomFieldModel
from nautobot.extras.models.relationships import RelationshipModel
from nautobot.extras.querysets import ConfigContextQuerySet, ScheduledJobExtendedQuerySet
from nautobot.extras.utils import extras_features, FeatureQuery, image_upload
from nautobot.utilities.utils import deepmerge, render_jinja2


# The JOB_LOGS variable is used to tell the JobLogEntry model the database to store to.
# We default this to job_logs, and creating at the Global level allows easy override
# during testing. This needs to point to the same physical database so that the
# foreign key relationship works, but needs its own connection to avoid JobLogEntry
# objects being created within transaction.atomic().
JOB_LOGS = "job_logs"


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
class ConfigContext(BaseModel, ChangeLoggedModel, ConfigContextSchemaValidationMixin):
    """
    A ConfigContext represents a set of arbitrary data available to any Device or VirtualMachine matching its assigned
    qualifiers (region, site, etc.). For example, the data stored in a ConfigContext assigned to site A and tenant B
    will be available to a Device in site A assigned to tenant B. Data is stored in JSON format.
    """

    name = models.CharField(
        max_length=100,
    )

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
    roles = models.ManyToManyField(to="dcim.DeviceRole", related_name="+", blank=True)
    device_types = models.ManyToManyField(to="dcim.DeviceType", related_name="+", blank=True)
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
        if type(self.data) is not dict:
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

    def get_config_context(self):
        """
        Return the rendered configuration context for a device or VM.
        """

        # always manually query for config contexts
        config_context_data = ConfigContext.objects.get_for_object(self).values_list("data", flat=True)

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
        if self.local_context_data and type(self.local_context_data) is not dict:
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

    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(max_length=200, blank=True)
    slug = AutoSlugField(populate_from="name", max_length=200, unique=None)
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
            type(self.data_schema) is not dict
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
class CustomLink(BaseModel, ChangeLoggedModel):
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
class ExportTemplate(BaseModel, ChangeLoggedModel, RelationshipModel):
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
        return "{}: {}".format(self.content_type, self.name)

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
        filename = "nautobot_{}{}".format(
            queryset.model._meta.verbose_name_plural,
            ".{}".format(self.file_extension) if self.file_extension else "",
        )
        response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)

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
    mimetype = models.CharField(max_length=50)

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
class GraphQLQuery(BaseModel, ChangeLoggedModel):
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
    object_id = models.UUIDField()
    parent = GenericForeignKey(ct_field="content_type", fk_field="object_id")
    image = models.ImageField(upload_to=image_upload, height_field="image_height", width_field="image_width")
    image_height = models.PositiveSmallIntegerField()
    image_width = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=50, blank=True)
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
# Jobs
#


@extras_features("job_results")
class Job(models.Model):
    """
    Dummy model used to generate permissions for jobs. Does not exist in the database.
    """

    class Meta:
        managed = False


@extras_features(
    "graphql",
)
class JobLogEntry(BaseModel):
    """Stores each log entry for the JobResult."""

    job_result = models.ForeignKey(to="extras.JobResult", on_delete=models.CASCADE, related_name="logs")
    log_level = models.CharField(max_length=32, choices=LogLevelChoices, default=LogLevelChoices.LOG_DEFAULT)
    grouping = models.CharField(max_length=JOB_LOG_MAX_GROUPING_LENGTH, default="main")
    message = models.TextField(blank=True)
    created = models.DateTimeField(default=timezone.now)
    # Storing both of the below as strings instead of using GenericForeignKey to support
    # compatibility with existing JobResult logs. GFK would pose a problem with dangling foreign-key
    # references, whereas this allows us to retain all records for as long as the entry exists.
    # This also simplifies migration from the JobResult Data field as these were stored as strings.
    log_object = models.CharField(max_length=JOB_LOG_MAX_LOG_OBJECT_LENGTH, null=True, blank=True)
    absolute_url = models.CharField(max_length=JOB_LOG_MAX_ABSOLUTE_URL_LENGTH, null=True, blank=True)

    def __str__(self):
        return self.message

    class Meta:
        ordering = ["created"]
        get_latest_by = "created"
        verbose_name_plural = "job log entries"


#
# Job results
#
@extras_features(
    "custom_fields",
    "custom_links",
    "graphql",
)
class JobResult(BaseModel, CustomFieldModel):
    """
    This model stores the results from running a user-defined report.
    """

    name = models.CharField(max_length=255)
    obj_type = models.ForeignKey(
        to=ContentType,
        related_name="job_results",
        verbose_name="Object types",
        limit_choices_to=FeatureQuery("job_results"),
        help_text="The object type to which this job result applies",
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)
    completed = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="+", blank=True, null=True
    )
    status = models.CharField(
        max_length=30,
        choices=JobResultStatusChoices,
        default=JobResultStatusChoices.STATUS_PENDING,
    )
    data = models.JSONField(encoder=DjangoJSONEncoder, null=True, blank=True)
    schedule = models.ForeignKey(to="extras.ScheduledJob", on_delete=models.SET_NULL, null=True, blank=True)
    """
    Although "data" is technically an unstructured field, we have a standard structure that we try to adhere to.

    This structure is created loosely as a superset of the formats used by Scripts and Reports in NetBox 2.10.

    Log Messages now go to their own object, the JobLogEntry.

    data = {
        "output": <optional string, such as captured stdout/stderr>,
    }
    """

    job_id = models.UUIDField(unique=True)

    class Meta:
        ordering = ["-created"]
        get_latest_by = "created"

    def __str__(self):
        return str(self.job_id)

    @property
    def duration(self):
        if not self.completed:
            return None

        duration = self.completed - self.created
        minutes, seconds = divmod(duration.total_seconds(), 60)

        return f"{int(minutes)} minutes, {seconds:.2f} seconds"

    @property
    def related_object(self):
        """Get the related object, if any, identified by the `obj_type`, `name`, and/or `job_id` fields.

        If `obj_type` is extras.Job, then the `name` is used to look up an extras.jobs.Job subclass based on the
        `class_path` of the Job subclass.
        Note that this is **not** the extras.models.Job model class nor an instance thereof.

        Else, if the the model class referenced by `obj_type` has a `name` field, our `name` field will be used
        to look up a corresponding model instance. This is used, for example, to look up a related `GitRepository`;
        more generally it can be used by any model that 1) has a unique `name` field and 2) needs to have a many-to-one
        relationship between JobResults and model instances.

        Else, the `obj_type` and `job_id` will be used together as a quasi-GenericForeignKey to look up a model
        instance whose PK corresponds to the `job_id`. This behavior is currently unused in the Nautobot core,
        but may be of use to plugin developers wishing to create JobResults that have a one-to-one relationship
        to plugin model instances.
        """
        from nautobot.extras.jobs import get_job  # needed here to avoid a circular import issue

        if self.obj_type == ContentType.objects.get(app_label="extras", model="job"):
            # Related object is an extras.Job subclass, our `name` matches its `class_path`
            return get_job(self.name)

        model_class = self.obj_type.model_class()

        if hasattr(model_class, "name"):
            # See if we have a many-to-one relationship from JobResult to model_class record, based on `name`
            try:
                return model_class.objects.get(name=self.name)
            except model_class.DoesNotExist:
                pass

        # See if we have a one-to-one relationship from JobResult to model_class record based on `job_id`
        try:
            return model_class.objects.get(id=self.job_id)
        except model_class.DoesNotExist:
            pass

        return None

    @property
    def related_name(self):
        """
        Similar to self.name, but if there's an appropriate `related_object`, use its name instead.
        """
        related_object = self.related_object
        if not related_object:
            return self.name
        if hasattr(related_object, "name"):
            return related_object.name
        return str(related_object)

    def get_absolute_url(self):
        return reverse("extras:jobresult", kwargs={"pk": self.pk})

    def set_status(self, status):
        """
        Helper method to change the status of the job result. If the target status is terminal, the  completion
        time is also set.
        """
        self.status = status
        if status in JobResultStatusChoices.TERMINAL_STATE_CHOICES:
            self.completed = timezone.now()

    @classmethod
    def enqueue_job(cls, func, name, obj_type, user, celery_kwargs=None, *args, schedule=None, **kwargs):
        """
        Create a JobResult instance and enqueue a job using the given callable

        func: The callable object to be enqueued for execution
        name: Name for the JobResult instance
        obj_type: ContentType to link to the JobResult instance obj_type
        user: User object to link to the JobResult instance
        celery_kwargs: Dictionary of kwargs to pass as **kwargs to Celery when job is queued
        args: additional args passed to the callable
        schedule: Optional ScheduledJob instance to link to the JobResult
        kwargs: additional kwargs passed to the callable
        """
        job_result = cls.objects.create(name=name, obj_type=obj_type, user=user, job_id=uuid.uuid4(), schedule=schedule)

        kwargs["job_result_pk"] = job_result.pk

        # Prepare kwargs that will be sent to Celery
        if celery_kwargs is None:
            celery_kwargs = {}

        func.apply_async(args=args, kwargs=kwargs, task_id=str(job_result.job_id), **celery_kwargs)

        return job_result

    def log(
        self,
        message,
        obj=None,
        level_choice=LogLevelChoices.LOG_DEFAULT,
        grouping="main",
        logger=None,
        use_default_db=False,
    ):
        """
        General-purpose API for storing log messages in a JobResult's 'data' field.

        message (str): Message to log
        obj (object): Object associated with this message, if any
        level_choice (LogLevelChoices): Message severity level
        grouping (str): Grouping to store the log message under
        logger (logging.logger): Optional logger to also output the message to
        use_default_db (bool): Use default database or JOB_LOGS
        """
        if level_choice not in LogLevelChoices.as_dict():
            raise Exception(f"Unknown logging level: {level_choice}")

        log = JobLogEntry(
            job_result=self,
            log_level=level_choice,
            grouping=grouping[:JOB_LOG_MAX_GROUPING_LENGTH],
            message=str(message),
            created=timezone.now().isoformat(),
            log_object=str(obj)[:JOB_LOG_MAX_LOG_OBJECT_LENGTH] if obj else None,
            absolute_url=obj.get_absolute_url()[:JOB_LOG_MAX_ABSOLUTE_URL_LENGTH]
            if hasattr(obj, "get_absolute_url")
            else None,
        )

        # If the override is provided, we want to use the default database(pass no using argument)
        # Otherwise we want to use a separate database here so that the logs are created immediately
        # instead of within transaction.atomic(). This allows us to be able to report logs when the jobs
        # are running, and allow us to rollback the database without losing the log entries.
        if use_default_db or not JOB_LOGS:
            log.save()
        else:
            log.save(using=JOB_LOGS)

        if logger:
            if level_choice == LogLevelChoices.LOG_FAILURE:
                log_level = logging.ERROR
            elif level_choice == LogLevelChoices.LOG_WARNING:
                log_level = logging.WARNING
            else:
                log_level = logging.INFO
            logger.log(log_level, str(message))


class ScheduledJobs(models.Model):
    """Helper table for tracking updates to scheduled tasks.
    This stores a single row with ident=1.  last_update is updated
    via django signals whenever anything is changed in the ScheduledJob model.
    Basically this acts like a DB data audit trigger.
    Doing this so we also track deletions, and not just insert/update.
    """

    ident = models.SmallIntegerField(default=1, primary_key=True, unique=True)
    last_update = models.DateTimeField(null=False)

    objects = ExtendedManager()

    @classmethod
    def changed(cls, instance, **kwargs):
        """This function acts as a signal handler to track changes to the scheduled job that is triggered before a change"""
        if not instance.no_changes:
            cls.update_changed()

    @classmethod
    def update_changed(cls, **kwargs):
        """This function acts as a signal handler to track changes to the scheduled job that is triggered after a change"""
        cls.objects.update_or_create(ident=1, defaults={"last_update": timezone.now()})

    @classmethod
    def last_change(cls):
        """This function acts as a getter for the last update on scheduled jobs"""
        try:
            return cls.objects.get(ident=1).last_update
        except cls.DoesNotExist:
            return None


class ScheduledJob(BaseModel):
    """Model representing a periodic task."""

    name = models.CharField(
        max_length=200,
        verbose_name="Name",
        help_text="Short Description For This Task",
    )
    task = models.CharField(
        max_length=200,
        verbose_name="Task Name",
        help_text='The name of the Celery task that should be run. (Example: "proj.tasks.import_contacts")',
    )
    job_class = models.CharField(
        max_length=255, verbose_name="Job Class", help_text="Name of the fully qualified Nautobot Job class path"
    )
    interval = models.CharField(choices=JobExecutionType, max_length=255)
    args = models.JSONField(blank=True, default=list, encoder=NautobotKombuJSONEncoder)
    kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    queue = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default=None,
        verbose_name="Queue Override",
        help_text="Queue defined in CELERY_TASK_QUEUES. Leave None for default queuing.",
    )
    one_off = models.BooleanField(
        default=False,
        verbose_name="One-off Task",
        help_text="If True, the schedule will only run the task a single time",
    )
    start_time = models.DateTimeField(
        verbose_name="Start Datetime",
        help_text="Datetime when the schedule should begin triggering the task to run",
    )
    enabled = models.BooleanField(
        default=True,
        verbose_name="Enabled",
        help_text="Set to False to disable the schedule",
    )
    last_run_at = models.DateTimeField(
        editable=False,
        blank=True,
        null=True,
        verbose_name="Most Recent Run",
        help_text="Datetime that the schedule last triggered the task to run. "
        "Reset to None if enabled is set to False.",
    )
    total_run_count = models.PositiveIntegerField(
        default=0,
        editable=False,
        verbose_name="Total Run Count",
        help_text="Running count of how many times the schedule has triggered the task",
    )
    date_changed = models.DateTimeField(
        auto_now=True,
        verbose_name="Last Modified",
        help_text="Datetime that this scheduled job was last modified",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Detailed description about the details of this scheduled job",
    )
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        help_text="User that requested the schedule",
    )
    approved_by_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        help_text="User that approved the schedule",
    )
    approval_required = models.BooleanField(default=False)
    approved_at = models.DateTimeField(
        editable=False,
        blank=True,
        null=True,
        verbose_name="Approval date/time",
        help_text="Datetime that the schedule was approved",
    )

    objects = ScheduledJobExtendedQuerySet.as_manager()
    no_changes = False

    def __str__(self):
        return f"{self.name}: {self.interval}"

    def get_absolute_url(self):
        return reverse("extras:scheduledjob", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        self.queue = self.queue or None
        if not self.enabled:
            self.last_run_at = None
        elif not self.last_run_at:
            # I'm not sure if this is a bug, or "works as designed", but if self.last_run_at is not set,
            # the celery beat scheduler will never pick up a recurring job. One-off jobs work just fine though.
            if self.interval in [
                JobExecutionType.TYPE_HOURLY,
                JobExecutionType.TYPE_DAILY,
                JobExecutionType.TYPE_WEEKLY,
            ]:
                # A week is 7 days, otherwise the iteration is set to 1
                multiplier = 7 if self.interval == JobExecutionType.TYPE_WEEKLY else 1
                # Set the "last run at" time to one interval before the scheduled start time
                self.last_run_at = self.start_time - timedelta(
                    **{JobExecutionType.CELERY_INTERVAL_MAP[self.interval]: multiplier},
                )

        super().save(*args, **kwargs)

    def clean(self):
        """
        Model Validation
        """
        if self.user and self.approved_by_user and self.user == self.approved_by_user:
            raise ValidationError("The requesting and approving users cannot be the same")
        # bitwise xor also works on booleans, but not on complex values
        if bool(self.approved_by_user) ^ bool(self.approved_at):
            raise ValidationError("Approval by user and approval time must either both be set or both be undefined")

    @property
    def schedule(self):
        if self.interval == JobExecutionType.TYPE_FUTURE:
            # This is one-time clocked task
            return clocked(clocked_time=self.start_time)

        return self.to_cron()

    @staticmethod
    def earliest_possible_time():
        return timezone.now() + timedelta(seconds=15)

    def to_cron(self):
        t = self.start_time
        if self.interval == JobExecutionType.TYPE_HOURLY:
            return schedules.crontab(minute=t.minute)
        elif self.interval == JobExecutionType.TYPE_DAILY:
            return schedules.crontab(minute=t.minute, hour=t.hour)
        elif self.interval == JobExecutionType.TYPE_WEEKLY:
            return schedules.crontab(minute=t.minute, hour=t.hour, day_of_week=t.weekday())
        raise ValueError(f"I do not know to convert {self.interval} to a Cronjob!")


signals.pre_delete.connect(ScheduledJobs.changed, sender=ScheduledJob)
signals.pre_save.connect(ScheduledJobs.changed, sender=ScheduledJob)
signals.post_save.connect(ScheduledJobs.update_changed, sender=ScheduledJob)


#
# Webhooks
#


@extras_features("graphql")
class Webhook(BaseModel, ChangeLoggedModel):
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
        unique_together = (
            "payload_url",
            "type_create",
            "type_update",
            "type_delete",
        )

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
        Render the body template, if defined. Otherwise, jump the context as a JSON object.
        """
        if self.body_template:
            return render_jinja2(self.body_template, context)
        else:
            return json.dumps(context, cls=JSONEncoder)

    def get_absolute_url(self):
        return reverse("extras:webhook", kwargs={"pk": self.pk})
