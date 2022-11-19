from django.contrib.contenttypes.models import ContentType
from django.db import models

from nautobot.extras.fields import ForeignKeyLimitedByContentTypes
from nautobot.extras.models.base_properties import BasePropertiesModel
from nautobot.extras.utils import extras_features, FeatureQuery
from nautobot.utilities.querysets import RestrictedQuerySet


class StatusQuerySet(RestrictedQuerySet):
    """Queryset for `Status` objects."""

    def get_for_model(self, model):
        """
        Return all `Status` assigned to the given model.
        """
        content_type = ContentType.objects.get_for_model(model._meta.concrete_model)
        return self.filter(content_types=content_type)

    def get_by_natural_key(self, name):
        return self.get(name=name)


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class Status(BasePropertiesModel):
    """Model for database-backend enum choice objects."""

    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="statuses",
        verbose_name="Content type(s)",
        limit_choices_to=FeatureQuery("statuses"),
        help_text="The content type(s) to which this status applies.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "statuses"


class StatusField(ForeignKeyLimitedByContentTypes):
    """
    Model database field that automatically limits custom choices.

    The limit_choices_to for the field are automatically derived from:

        - the content-type to which the field is attached (e.g. `dcim.device`)
    """

    def set_defaults(self, **kwargs):
        kwargs.setdefault("to", Status)
        return kwargs


class StatusModel(models.Model):
    """
    Abstract base class for any model which may have statuses.
    """

    status = StatusField(
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_related",  # e.g. dcim_device_related
    )

    class Meta:
        abstract = True
