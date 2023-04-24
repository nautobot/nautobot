from functools import partialmethod

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import force_str
from django.utils.hashable import make_hashable

from nautobot.core.models.fields import ForeignKeyLimitedByContentTypes
from nautobot.core.models.name_color_content_types import NameColorContentTypesModel
from nautobot.extras.utils import extras_features, FeatureQuery


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class Status(NameColorContentTypesModel):
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

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("to", Status)
        kwargs.setdefault("on_delete", models.PROTECT)
        super().__init__(*args, **kwargs)

    def get_limit_choices_to(self):
        return {"content_types": ContentType.objects.get_for_model(self.model)}

    def contribute_to_class(self, cls, *args, **kwargs):
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
        super().contribute_to_class(cls, *args, **kwargs)

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


class StatusModel(models.Model):
    """
    Abstract base class for any model which may have statuses.
    """

    status = StatusField()

    class Meta:
        abstract = True
