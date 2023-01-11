from django.contrib.contenttypes.models import ContentType
from django.db.models import ForeignKey
from django_extensions.db.fields import AutoSlugField as _AutoSlugField

from nautobot.utilities.forms import DynamicModelChoiceField
from nautobot.utilities.utils import slugify_dots_to_dashes  # noqa: F401


class AutoSlugField(_AutoSlugField):
    """AutoSlugField

    By default, sets editable=True, blank=True, max_length=100, overwrite_on_add=False, unique=True
    Required arguments:
    populate_from
        Specifies which field, list of fields, or model method
        the slug will be populated from.

        populate_from can traverse a ForeignKey relationship
        by using Django ORM syntax:
            populate_from = 'related_model__field'

    Optional arguments:

    separator
        Defines the used separator (default: '-')

    overwrite
        If set to True, overwrites the slug on every save (default: False)

    overwrite_on_add
        If set to True, overwrites the provided slug on initial creation (default: False)

    slugify_function
        Defines the function which will be used to "slugify" a content
        (default: :py:func:`~django.template.defaultfilters.slugify` )

    It is possible to provide custom "slugify" function with
    the ``slugify_function`` function in a model class.

    ``slugify_function`` function in a model class takes priority over
    ``slugify_function`` given as an argument to :py:class:`~AutoSlugField`.

    Example

    .. code-block:: python
        # models.py

        from django.db import models
        from django_extensions.db.fields import AutoSlugField

        class MyModel(models.Model):
            def slugify_function(self, content):
                return content.replace('_', '-').lower()

            title = models.CharField(max_length=42)
            slug = AutoSlugField(populate_from='title')

    Taken from django_extensions AutoSlugField Documentation.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 100)
        kwargs.setdefault("editable", True)
        kwargs.setdefault("overwrite_on_add", False)
        kwargs.setdefault("unique", True)
        super().__init__(*args, **kwargs)

    def get_slug_fields(self, model_instance, lookup_value):
        """Workaround for https://github.com/django-extensions/django-extensions/issues/1713."""
        try:
            return super().get_slug_fields(model_instance, lookup_value)
        except AttributeError:
            return ""


class ForeignKeyLimitedByContentTypes(ForeignKey):
    """
    An abstract model field that automatically restricts ForeignKey options based on content_types.

    For instance, if the model "Role" contains two records: role_1 and role_2, role_1's content_types
    are set to "dcim.site" and "dcim.device" while the role_2's content_types are set to
    "circuit.circuit" and "dcim.site."

    Then, for the field `role` on the Device model, role_1 is the only Role that is available,
    while role_1 & role_2 are both available for the Site model.

    The limit_choices_to for the field are automatically derived from:
        - the content-type to which the field is attached (e.g. `dcim.device`)
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("null", True)
        super().__init__(**kwargs)

    def get_limit_choices_to(self):
        return {"content_types": ContentType.objects.get_for_model(self.model)}

    def formfield(self, **kwargs):
        """Return a prepped formfield for use in model forms."""
        defaults = {
            "form_class": DynamicModelChoiceField,
            "queryset": self.related_model.objects.all(),
            # label_lower e.g. "dcim.device"
            "query_params": {"content_types": self.model._meta.label_lower},
        }
        defaults.update(**kwargs)
        return super().formfield(**defaults)
