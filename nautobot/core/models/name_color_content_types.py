from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

from nautobot.core.choices import ColorChoices
from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.fields import ColorField
from nautobot.core.models.querysets import RestrictedQuerySet

# Importing CustomFieldModel, ChangeLoggedModel, RelationshipModel from  nautobot.extras.models
# caused circular import error
from nautobot.extras.models.customfields import CustomFieldModel
from nautobot.extras.models.change_logging import ChangeLoggedModel
from nautobot.extras.models.relationships import RelationshipModel
from nautobot.extras.models.mixins import DynamicGroupMixin, NotesMixin


class ContentTypeRelatedQuerySet(RestrictedQuerySet):
    def get_for_model(self, model):
        """
        Return all `self.model` instances assigned to the given model.
        """
        content_type = ContentType.objects.get_for_model(model._meta.concrete_model)
        return self.filter(content_types=content_type)

    # TODO(timizuo): Merge into get_for_model; Cant do this now cause it would require alot
    #  of refactoring
    def get_for_models(self, models_):
        """
        Return all `self.model` instances assigned to the given `_models`.
        """
        q = Q()
        for model in models_:
            q |= Q(app_label=model._meta.app_label, model=model._meta.model_name)
        content_types = ContentType.objects.filter(q)
        return self.filter(content_types__in=content_types)


# TODO(timizuo): Inheriting from OrganizationalModel here causes partial import error
class NameColorContentTypesModel(
    BaseModel,
    ChangeLoggedModel,
    CustomFieldModel,
    RelationshipModel,
    NotesMixin,
    DynamicGroupMixin,
):
    """
    This abstract base properties model contains fields and functionality that are
    shared amongst models that requires these fields: name, color, content_types and description.
    """

    content_types = models.ManyToManyField(
        to=ContentType,
        help_text="The content type(s) to which this model applies.",
    )
    name = models.CharField(max_length=100, unique=True)
    color = ColorField(default=ColorChoices.COLOR_GREY)
    description = models.CharField(
        max_length=200,
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
