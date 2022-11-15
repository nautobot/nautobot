from django.contrib.contenttypes.models import ContentType
from django.db import models

from nautobot.core.fields import AutoSlugField
from nautobot.core.models import BaseModel
from nautobot.extras.fields import LimitedChoiceField
from nautobot.extras.models import ChangeLoggedModel, CustomFieldModel, RelationshipModel
from nautobot.extras.models.mixins import NotesMixin
from nautobot.extras.querysets import ContentTypeRelatedQuerySet
from nautobot.extras.utils import RoleModelsQuery, extras_features
from nautobot.utilities.choices import ColorChoices
from nautobot.utilities.fields import ColorField


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class Role(BaseModel, ChangeLoggedModel, CustomFieldModel, RelationshipModel, NotesMixin):
    # TODO(timizuo): Create abstract model for this because Role, Status and Tags
    #  all contain similar fields

    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="roles",
        verbose_name="Content type(s)",
        limit_choices_to=RoleModelsQuery(),
        help_text="The content type(s) to which this role applies.",
    )
    name = models.CharField(max_length=50, unique=True)
    color = ColorField(default=ColorChoices.COLOR_GREY)
    slug = AutoSlugField(populate_from="name", max_length=50)
    description = models.CharField(
        max_length=200,
        blank=True,
    )

    objects = ContentTypeRelatedQuerySet.as_manager()

    csv_headers = ["name", "slug", "color", "content_types", "description"]
    clone_fields = ["color", "content_types"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    # TODO(timizuo): When view url has been implemented for role; visit this
    # def get_absolute_url(self):
    #     return reverse("extras:status", args=[self.slug])

    def to_csv(self):
        labels = ",".join(f"{ct.app_label}.{ct.model}" for ct in self.content_types.all())
        return (
            self.name,
            self.slug,
            self.color,
            f'"{labels}"',  # Wrap labels in double quotes for CSV
            self.description,
        )


class RoleField(LimitedChoiceField):
    """Model database field that automatically limits role choices
    depending on the model implementing it.
    """

    def set_defaults(self, **kwargs):
        kwargs.setdefault("to", Role)
        return super().set_defaults(**kwargs)


class RoleModel(models.Model):
    """
    Abstract base class for any model which may have roles.
    """

    role = RoleField(
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_related",  # e.g. dcim_device_related
    )

    class Meta:
        abstract = True
