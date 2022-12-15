from functools import partialmethod

from django.utils.encoding import force_str
from django.utils.hashable import make_hashable


class SetFieldColorAndDisplayMixin:
    """
    Mixin class that extends the model Field class with get_FIELD_NAME_display and get_FIELD_NAME_color methods.

    Take note that FIELD_NAME would be the name of the model field that uses this mixin. for example:

    class StatusField(SetFieldColorAndDisplayMixin, models.ForeignKey):
        ...

    class Device(models.Model):
        ...
        status = StatusField(...)

    The Device instance would now have access these methods get_status_color() and get_status_color.
    """

    def contribute_to_class(self, cls, name, *args, private_only=False, **kwargs):
        """
        Overload default so that we can assert that `.get_FOO_display` is
        attached to any model that is using a `ForeignKeyLimitedByContentTypes`.

        Using `.contribute_to_class()` is how field objects get added to the model
        at during the instance preparation. This is also where any custom model
        methods are hooked in. So in short this method asserts that any time a
        `ForeignKeyLimitedByContentTypes` is added to a model, that model also gets a
        `.get_`self.name`_display()` and a `.get_`self.name`_color()` method without
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

            I am added to the model via `ForeignKeyLimitedByContentTypes.contribute_to_class()`.
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
