from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.html import format_html

from nautobot.core.choices import ColorChoices
from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, BaseModel, ContentTypeRelatedQuerySet
from nautobot.core.models.fields import ColorField
from nautobot.core.templatetags import helpers
from nautobot.extras.models.change_logging import ChangeLoggedModel

# Importing CustomFieldModel, ChangeLoggedModel, RelationshipModel from  nautobot.extras.models
# caused circular import error
from nautobot.extras.models.customfields import CustomFieldModel
from nautobot.extras.models.mixins import ContactMixin, DynamicGroupsModelMixin, NotesMixin, SavedViewMixin
from nautobot.extras.models.relationships import RelationshipModel


# TODO(timizuo): Inheriting from OrganizationalModel here causes partial import error
class NameColorContentTypesModel(
    ChangeLoggedModel,
    ContactMixin,
    CustomFieldModel,
    DynamicGroupsModelMixin,
    NotesMixin,
    RelationshipModel,
    SavedViewMixin,
    BaseModel,
):
    """
    This abstract base properties model contains fields and functionality that are
    shared amongst models that requires these fields: name, color, content_types and description.
    """

    content_types = models.ManyToManyField(
        to=ContentType,
        help_text="The content type(s) to which this model applies.",
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    color = ColorField(default=ColorChoices.COLOR_GREY)
    description = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
    )

    objects = BaseManager.from_queryset(ContentTypeRelatedQuerySet)()

    clone_fields = ["color", "content_types"]

    class Meta:
        ordering = ["name"]
        abstract = True

    def __str__(self):
        return self.name

    def get_content_types(self):
        return ",".join(f"{ct.app_label}.{ct.model}" for ct in self.content_types.all())

    def get_color_display(self):
        if self.color:
            return format_html(
                '<span class="label color-block" style="background-color: #{}">&nbsp;</span>', self.color
            )
        return helpers.placeholder(self.color)
