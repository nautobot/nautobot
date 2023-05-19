from django.contrib.contenttypes.models import ContentType
from django.db import models

from nautobot.core.models.fields import ForeignKeyLimitedByContentTypes
from nautobot.core.models.name_color_content_types import NameColorContentTypesModel
from nautobot.extras.utils import RoleModelsQuery, extras_features


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
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

    csv_headers = ["name", "weight", "color", "content_types", "description"]

    class Meta:
        ordering = ("weight", "name")

    def to_csv(self):
        return (
            self.name,
            self.weight,
            self.color,
            self.get_content_types(),
            self.description,
        )


class RoleField(ForeignKeyLimitedByContentTypes):
    """Model database field that automatically limits role choices
    depending on the model implementing it.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("to", Role)
        kwargs.setdefault("on_delete", models.PROTECT)
        super().__init__(*args, **kwargs)
