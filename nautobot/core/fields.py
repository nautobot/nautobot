from django_extensions.db.fields import AutoSlugField as _AutoSlugField

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
