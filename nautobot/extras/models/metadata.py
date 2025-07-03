from datetime import date, datetime, timezone

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.fields import JSONArrayField
from nautobot.core.models.generics import PrimaryModel
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.core.settings_funcs import is_truthy
from nautobot.extras.choices import MetadataTypeDataTypeChoices
from nautobot.extras.models.change_logging import ChangeLoggedModel
from nautobot.extras.models.contacts import Contact, Team
from nautobot.extras.utils import extras_features, FeatureQuery


class MetadataTypeManager(BaseManager.from_queryset(RestrictedQuerySet)):
    use_in_migrations = True

    def get_for_model(self, model):
        """Return all MetadataTypes assigned to the given model."""
        concrete_model = model._meta.concrete_model
        cache_key = f"{self.get_for_model.cache_key_prefix}.{concrete_model._meta.label_lower}"
        queryset = cache.get(cache_key)
        if queryset is None:
            content_type = ContentType.objects.get_for_model(concrete_model)
            queryset = self.get_queryset().filter(content_types=content_type)
            cache.set(cache_key, queryset)
        return queryset

    get_for_model.cache_key_prefix = "nautobot.extras.metadatatype.get_for_model"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class MetadataType(PrimaryModel):
    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="metadata_types",
        limit_choices_to=FeatureQuery("metadata"),
        help_text="The object type(s) to which Metadata of this type can be applied.",
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    data_type = models.CharField(
        max_length=50,
        choices=MetadataTypeDataTypeChoices,
        help_text="The type of data allowed for any Metadata of this type.",
    )
    # TODO: validation_minimum, validation_maximum, validation_regex?
    # TODO: weight, grouping, advanced_ui?

    objects = MetadataTypeManager()
    clone_fields = ["data_type"]
    documentation_static_path = "docs/user-guide/platform-functionality/objectmetadata.html"

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if self.present_in_database:
            # Check immutable fields
            database_object = self.__class__.objects.get(pk=self.pk)
            if self.data_type != database_object.data_type:
                raise ValidationError({"data_type": "Type cannot be changed once created"})

        # Choices can be set only on selection fields
        if self.choices.exists() and self.data_type not in (
            MetadataTypeDataTypeChoices.TYPE_SELECT,
            MetadataTypeDataTypeChoices.TYPE_MULTISELECT,
        ):
            raise ValidationError("Choices may be set only for select/multi-select data_type.")


@extras_features(
    "custom_validators",
    "graphql",
    "webhooks",
)
class MetadataChoice(ChangeLoggedModel, BaseModel):
    """Store the possible set of values for a select/multi-select metadata type."""

    metadata_type = models.ForeignKey(
        to=MetadataType,
        on_delete=models.CASCADE,
        related_name="choices",
        limit_choices_to=models.Q(
            data_type__in=[MetadataTypeDataTypeChoices.TYPE_SELECT, MetadataTypeDataTypeChoices.TYPE_MULTISELECT]
        ),
    )
    value = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    weight = models.PositiveSmallIntegerField(default=100, help_text="Higher weights appear later in the list")
    is_metadata_associable_model = False

    documentation_static_path = "docs/user-guide/platform-functionality/objectmetadata.html"

    class Meta:
        ordering = ["metadata_type", "weight", "value"]
        unique_together = ["metadata_type", "value"]

    def __str__(self):
        return self.value

    def clean(self):
        super().clean()

        if self.present_in_database:
            # Check immutable fields
            database_object = self.__class__.objects.get(pk=self.pk)
            if self.metadata_type != database_object.metadata_type:
                raise ValidationError({"metadata_type": "Cannot be changed once created"})

        if self.metadata_type.data_type not in (
            MetadataTypeDataTypeChoices.TYPE_SELECT,
            MetadataTypeDataTypeChoices.TYPE_MULTISELECT,
        ):
            raise ValidationError(
                {"metadata_type": "Metadata choices can only be assigned to select/multiselect data_type."}
            )
        # TODO: enforce validation_minimum, validation_maximum, validation_regex like CustomFieldChoice does?

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # TODO: on change of value, enqueue background task to go through all existing metadata and update them,
        #       like CustomFieldChoice does?
        # TODO: Alternately, should we let Metadata just have a FK directly to its corresponding MetadataTypeChoice?

    def delete(self, *args, **kwargs):
        # TODO: should we behave like CustomFieldChoice and raise a ProtectedError if this choice is in use anywhere?
        super().delete(*args, **kwargs)


class ObjectMetadataManager(BaseManager.from_queryset(RestrictedQuerySet)):
    use_in_migrations = True

    def get_for_object(self, instance):
        """Return all ObjectMetadatas assigned to the given instance."""
        assigned_object_type = ContentType.objects.get_for_model(instance)
        assigned_object_id = instance.pk
        queryset = self.get_queryset().filter(
            assigned_object_type=assigned_object_type, assigned_object_id=assigned_object_id
        )
        return queryset


@extras_features(
    "custom_validators",
    "graphql",
    "webhooks",
)
class ObjectMetadata(ChangeLoggedModel, BaseModel):
    metadata_type = models.ForeignKey(
        to=MetadataType,
        on_delete=models.PROTECT,
        related_name="object_metadata",
    )
    contact = models.ForeignKey(
        to=Contact,
        on_delete=models.PROTECT,
        related_name="object_metadata",
        blank=True,
        null=True,
    )
    team = models.ForeignKey(
        to=Team,
        on_delete=models.PROTECT,
        related_name="object_metadata",
        blank=True,
        null=True,
    )
    scoped_fields = JSONArrayField(
        base_field=models.CharField(
            max_length=CHARFIELD_MAX_LENGTH,
        ),
        blank=True,
        help_text="List of scoped fields, only direct fields on the model",
    )
    _value = models.JSONField(
        blank=True,
        null=True,
        help_text="Relevant data value to an object field or a set of object fields",
    )
    assigned_object_type = models.ForeignKey(to=ContentType, on_delete=models.SET_NULL, null=True, related_name="+")
    assigned_object_id = models.UUIDField(db_index=True)
    assigned_object = GenericForeignKey(ct_field="assigned_object_type", fk_field="assigned_object_id")

    objects = ObjectMetadataManager()
    natural_key_field_names = ["pk"]
    documentation_static_path = "docs/user-guide/platform-functionality/objectmetadata.html"
    is_metadata_associable_model = False

    class Meta:
        ordering = ["metadata_type"]
        verbose_name_plural = "object metadata"

        indexes = [
            models.Index(
                name="assigned_object",
                fields=["assigned_object_type", "assigned_object_id"],
            ),
            models.Index(
                name="assigned_object_contact",
                fields=["assigned_object_type", "assigned_object_id", "contact"],
            ),
            models.Index(
                name="assigned_object_team",
                fields=["assigned_object_type", "assigned_object_id", "team"],
            ),
        ]

    @property
    def value(self):
        if self.metadata_type.data_type == MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM:
            return None
        else:
            return self._value

    @value.setter
    def value(self, v):
        if self.metadata_type.data_type == MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM:
            if v is not None:
                raise ValidationError(
                    f"{v} is an invalid value for metadata type data type {self.metadata_type.data_type}"
                )
        else:
            self._value = v
        self.clean()

    def __str__(self):
        if self.metadata_type.data_type == MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM:
            return f"{self.metadata_type} - {self.assigned_object} - {self.contact or self.team}"
        return f"{self.metadata_type} - {self.assigned_object} - {self.value}"

    def validated_save(self, *args, **kwargs):
        # call clean() first so that the data type-conversion is done first
        # so that clean_fields() would not raise any errors
        self.clean()
        return super().validated_save(*args, **kwargs)

    validated_save.alters_data = True

    def clean(self):
        """
        Validate a value according to the field's type validation rules.

        Returns the value, possibly cleaned up
        """
        super().clean()
        value = self.value
        metadata_type_data_type = self.metadata_type.data_type
        if self.present_in_database:
            # Check immutable fields
            database_object = self.__class__.objects.get(pk=self.pk)
            if self.metadata_type != database_object.metadata_type:
                raise ValidationError({"metadata_type": "Cannot be changed once created"})
        # Validate the assigned_object_type is allowed in metadata_type's content_types
        if not self.metadata_type.content_types.filter(pk=self.assigned_object_type.id).exists():
            raise ValidationError(
                f"Assigned Object Type {self.assigned_object_type} is not allowed by Metadata Type {self.metadata_type}"
            )
        # Check for MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM first
        if metadata_type_data_type == MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM:
            if value is not None:
                raise ValidationError(f"A value cannot be specified for type {metadata_type_data_type}")
            if self.contact is None and self.team is None:
                raise ValidationError("Either a contact or a team must be specified")
            if self.contact is not None and self.team is not None:
                raise ValidationError("A contact and a team cannot be both specified at once")
        elif value is None:
            raise ValidationError(
                f"value is a required field that cannot be empty for metadata type {metadata_type_data_type}."
            )
        else:
            # Validate text field
            if metadata_type_data_type in (
                MetadataTypeDataTypeChoices.TYPE_TEXT,
                MetadataTypeDataTypeChoices.TYPE_URL,
                MetadataTypeDataTypeChoices.TYPE_MARKDOWN,
            ):
                if not isinstance(value, str):
                    raise ValidationError("Value must be a string")
                # TODO uncomment this when MetaDataType validation_minimum, validation_maximum and validation_regex fields are implemented
                # if self.metadata_type.validation_minimum is not None and len(value) < self.metadata_type.validation_minimum:
                #     raise ValidationError(f"Value must be at least {self.metadata_type.validation_minimum} characters in length")
                # if self.metadata_type.validation_maximum is not None and len(value) > self.metadata_type.validation_maximum:
                #     raise ValidationError(f"Value must not exceed {self.metadata_type.validation_maximum} characters in length")
                # if self.metadata_type.validation_regex and not re.search(self.metadata_type.validation_regex, value):
                #     raise ValidationError(f"Value must match regex '{self.metadata_type.validation_regex}'")

            # Validate JSON
            elif metadata_type_data_type == MetadataTypeDataTypeChoices.TYPE_JSON:
                pass
                # TODO uncomment this when MetaDataType validation_minimum, validation_maximum and validation_regex fields are implemented
                # if (
                #     self.metadata_type.validation_regex
                #     or self.metadata_type.validation_minimum is not None
                #     or self.metadata_type.validation_maximum is not None
                # ):
                #     json_value = json.dumps(value)
                #     if (
                #         self.metadata_type.validation_minimum is not None
                #         and len(json_value) < self.metadata_type.validation_minimum
                #     ):
                #         raise ValidationError(
                #             f"Value must be at least {self.metadata_type.validation_minimum} characters in length"
                #         )
                #     if (
                #         self.metadata_type.validation_maximum is not None
                #         and len(json_value) > self.metadata_type.validation_maximum
                #     ):
                #         raise ValidationError(
                #             f"Value must not exceed {self.metadata_type.validation_maximum} characters in length"
                #         )
                #     if self.metadata_type.validation_regex and not re.search(
                #         self.metadata_type.validation_regex, json_value
                #     ):
                #         raise ValidationError(f"Value must match regex '{self.metadata_type.validation_regex}'")

            # Validate integer
            elif metadata_type_data_type == MetadataTypeDataTypeChoices.TYPE_INTEGER:
                try:
                    value = int(value)
                except ValueError:
                    raise ValidationError("Value must be an integer.")
                # TODO uncomment this when MetaDataType validation_minimum, validation_maximum and validation_regex fields are implemented
                # if self.metadata_type.validation_minimum is not None and value < self.metadata_type.validation_minimum:
                #     raise ValidationError(f"Value must be at least {self.metadata_type.validation_minimum}")
                # if self.metadata_type.validation_maximum is not None and value > self.metadata_type.validation_maximum:
                #     raise ValidationError(f"Value must not exceed {self.metadata_type.validation_maximum}")
            # Validate integer
            elif metadata_type_data_type == MetadataTypeDataTypeChoices.TYPE_FLOAT:
                try:
                    value = float(value)
                except ValueError:
                    raise ValidationError("Value must be a float.")
            # Validate boolean
            elif metadata_type_data_type == MetadataTypeDataTypeChoices.TYPE_BOOLEAN:
                try:
                    value = is_truthy(value)
                except ValueError as exc:
                    raise ValidationError("Value must be true or false.") from exc

            # Validate date
            elif metadata_type_data_type == MetadataTypeDataTypeChoices.TYPE_DATE:
                if not isinstance(value, date):
                    try:
                        datetime.strptime(value, "%Y-%m-%d")
                    except TypeError:
                        raise ValidationError("Value must be a date or str object.")
                    except ValueError:
                        raise ValidationError("Date values must be in the format YYYY-MM-DD.")
            # Validate datetime
            elif metadata_type_data_type == MetadataTypeDataTypeChoices.TYPE_DATETIME:
                if isinstance(value, datetime):
                    # check if datetime object has tzinfo
                    if value.tzinfo is None:
                        value = value.replace(tzinfo=timezone.utc)  # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
                    value = value.replace(microsecond=0).isoformat()  # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
                else:
                    acceptable_datetime_formats = [
                        "YYYY-MM-DDTHH:MM:SS",
                        "YYYY-MM-DDTHH:MM:SS(+,-)zzzz",
                        "YYYY-MM-DDTHH:MM:SS(+,-)zz:zz",
                    ]
                    try:
                        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
                    except ValueError:
                        try:
                            # No time zone info entered so assume UTC timezone
                            datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
                            value += "+0000"
                        except ValueError:
                            raise ValidationError(
                                f"Datetime values must be in the following formats {acceptable_datetime_formats}"
                            )
                    except TypeError:
                        raise ValidationError("Value must be a datetime or str object.")
            # Validate selected choice
            elif metadata_type_data_type == MetadataTypeDataTypeChoices.TYPE_SELECT:
                if value not in self.metadata_type.choices.values_list("value", flat=True):
                    raise ValidationError(
                        f"Invalid choice ({value}). Available choices are: {', '.join(self.metadata_type.choices.values_list('value', flat=True))}"
                    )

            elif metadata_type_data_type == MetadataTypeDataTypeChoices.TYPE_MULTISELECT:
                if isinstance(value, str):
                    value = value.split(",")
                if not set(value).issubset(self.metadata_type.choices.values_list("value", flat=True)):
                    raise ValidationError(
                        f"Invalid choice(s) ({value}). Available choices are: {', '.join(self.metadata_type.choices.values_list('value', flat=True))}"
                    )
        self._value = value

        # Check if there is any intersections of scoped_fields of ObjectMetadata instances in the database.
        object_metadata_scoped_fields = (
            ObjectMetadata.objects.filter(
                metadata_type=self.metadata_type,
                assigned_object_type=self.assigned_object_type,
                assigned_object_id=self.assigned_object_id,
            )
            .exclude(pk=self.pk)
            .values_list("scoped_fields", flat=True)
        )
        duplicate_scoped_fields_list = set([])

        # TODO Make sure that scoped fields are all direct fields on the assigned_object_type model

        for scoped_fields in object_metadata_scoped_fields:
            duplicate_scoped_fields_list |= set(self.scoped_fields).intersection(scoped_fields)
            # if self.scoped_fields or scoped_fields are [] which means all fields are scoped
            # That means any fields in self.scoped_fields or scoped_fields are considered overlapped
            if not self.scoped_fields:
                raise ValidationError(
                    {
                        "scoped_fields": f"This Object Metadata {self} scoping all the fields for {self.assigned_object} has overlapped with the scoped fields of other Object Metadata instances."
                    }
                )
            if not scoped_fields:
                raise ValidationError(
                    {
                        "scoped_fields": f"There are other Object Metadata instances of metadata type {self.metadata_type} scoping all the fields for {self.assigned_object}"
                    }
                )

        if duplicate_scoped_fields_list:
            raise ValidationError(
                {
                    "scoped_fields": f"There are other Object Metadata instances of metadata type {self.metadata_type} scoping the same fields {duplicate_scoped_fields_list} for {self.assigned_object}"
                }
            )
