from django.contrib.contenttypes.models import ContentType
from django.db import models

from nautobot.core.fields import ForeignKeyLimitedByContentTypes
from nautobot.core.models.mixins import SetFieldColorAndDisplayMixin
from nautobot.core.models.name_color_content_types import NameColorContentTypesModel
from nautobot.extras.utils import RoleModelsQuery, extras_features


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class Role(NameColorContentTypesModel):
    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="roles",
        verbose_name="Content type(s)",
        limit_choices_to=RoleModelsQuery(),
        help_text="The content type(s) to which this role applies.",
    )
    weight = models.PositiveSmallIntegerField(null=True, blank=True)


class RoleField(SetFieldColorAndDisplayMixin, ForeignKeyLimitedByContentTypes):
    """Model database field that automatically limits role choices
    depending on the model implementing it.
    """

    def set_defaults(self, **kwargs):
        kwargs.setdefault("to", Role)
        return super().set_defaults(**kwargs)


class RoleModelMixin(models.Model):
    """
    Abstract base class for any model which may have roles.
    """

    role = RoleField(
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_related",  # e.g. dcim_device_related
    )

    class Meta:
        abstract = True
