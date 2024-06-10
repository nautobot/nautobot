from django.core.validators import ValidationError
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseModel
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.choices import MetadataTypeDataTypeChoices
from nautobot.extras.models.change_logging import ChangeLoggedModel
from nautobot.extras.utils import extras_features


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class MetadataType(PrimaryModel):
    # TODO?
    # content_types = models.ManyToManyField(
    #     to=ContentType,
    #     related_name="metadata_types",
    #     # TODO limit_choices_to=FeatureQuery("metadata"),
    #     help_text="The object type(s) to which this metadata type applies.",
    # )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    data_type = models.CharField(
        max_length=50,
        choices=MetadataTypeDataTypeChoices,
        help_text="The type of data allowed for any Metadata of this type.",
    )
    # TODO: validation_minimum, validation_maximum, validation_regex?
    # TODO: weight, grouping, advanced_ui?

    clone_fields = ["data_type"]
    documentation_static_path = "docs/user-guide/platform-functionality/metadata.html"

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

    documentation_static_path = "docs/user-guide/platform-functionality/metadata.html"

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
