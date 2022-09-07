from functools import partialmethod

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.hashable import make_hashable
from nautobot.extras.models.mixins import NotesMixin

from nautobot.extras.utils import extras_features, FeatureQuery
from nautobot.extras.models import ChangeLoggedModel
from nautobot.extras.models.customfields import CustomFieldModel
from nautobot.extras.models.relationships import RelationshipModel
from nautobot.core.fields import AutoSlugField
from nautobot.core.models import BaseModel
from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.utilities.choices import ColorChoices
from nautobot.utilities.forms import DynamicModelChoiceField
from nautobot.utilities.fields import ColorField


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
class Status(BaseModel, ChangeLoggedModel, CustomFieldModel, RelationshipModel, NotesMixin):
    """Model for database-backend enum choice objects."""

    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="statuses",
        verbose_name="Content type(s)",
        limit_choices_to=FeatureQuery("statuses"),
        help_text="The content type(s) to which this status applies.",
    )
    name = models.CharField(max_length=50, unique=True)
    color = ColorField(default=ColorChoices.COLOR_GREY)
    slug = AutoSlugField(populate_from="name", max_length=50)
    description = models.CharField(
        max_length=200,
        blank=True,
    )

    objects = StatusQuerySet.as_manager()

    csv_headers = ["name", "slug", "color", "content_types", "description"]
    clone_fields = ["color", "content_types"]

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "statuses"

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    def get_absolute_url(self):
        return reverse("extras:status", args=[self.slug])

    def to_csv(self):
        labels = ",".join(f"{ct.app_label}.{ct.model}" for ct in self.content_types.all())
        return (
            self.name,
            self.slug,
            self.color,
            f'"{labels}"',  # Wrap labels in double quotes for CSV
            self.description,
        )


class StatusField(models.ForeignKey):
    """
    Model database field that automatically limits custom choices.

    The limit_choices_to for the field are automatically derived from:

        - the content-type to which the field is attached (e.g. `dcim.device`)
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("to", Status)
        kwargs.setdefault("null", True)
        super().__init__(**kwargs)

    def get_limit_choices_to(self):
        return {"content_types": ContentType.objects.get_for_model(self.model)}

    def contribute_to_class(self, cls, name, *args, private_only=False, **kwargs):
        """
        Overload default so that we can assert that `.get_FOO_display` is
        attached to any model that is using a `StatusField`.

        Using `.contribute_to_class()` is how field objects get added to the model
        at during the instance preparation. This is also where any custom model
        methods are hooked in. So in short this method asserts that any time a
        `StatusField` is added to a model, that model also gets a
        `.get_status_display()` and a `.get_status_color()` method without
        having to define it on the model yourself.
        """
        super().contribute_to_class(cls, name, *args, private_only=private_only, **kwargs)

        def _get_FIELD_display(self, field):
            """
            Closure to replace default model method of the same name.

            Cargo-culted from `django.db.models.base.Model._get_FIELD_display`
            """
            choices = field.get_choices()
            value = getattr(self, field.attname)
            choices_dict = dict(make_hashable(choices))
            # force_str() to coerce lazy strings.
            return force_str(choices_dict.get(make_hashable(value), value), strings_only=True)

        # Install `.get_FOO_display()` onto the model using our own version.
        if f"get_{self.name}_display" not in cls.__dict__:
            setattr(
                cls,
                f"get_{self.name}_display",
                partialmethod(_get_FIELD_display, field=self),
            )

        def _get_FIELD_color(self, field):
            """
            Return `self.FOO.color` (where FOO is field name).

            I am added to the model via `StatusField.contribute_to_class()`.
            """
            field_method = getattr(self, field.name)
            return getattr(field_method, "color")

        # Install `.get_FOO_color()` onto the model using our own version.
        if f"get_{self.name}_color" not in cls.__dict__:
            setattr(
                cls,
                f"get_{self.name}_color",
                partialmethod(_get_FIELD_color, field=self),
            )

    def formfield(self, **kwargs):
        """Return a prepped formfield for use in model forms."""
        defaults = {
            "form_class": DynamicModelChoiceField,
            "queryset": Status.objects.all(),
            # label_lower e.g. "dcim.device"
            "query_params": {"content_types": self.model._meta.label_lower},
        }
        defaults.update(**kwargs)
        return super().formfield(**defaults)


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
