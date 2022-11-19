from django.contrib.contenttypes.models import ContentType
from django.db import models

from nautobot.utilities.forms import DynamicModelChoiceField


class ForeignKeyLimitedByContentTypes(models.ForeignKey):
    """
    An abstract model field that automatically restricts ForeignKey options based on content_types.

    For instance, if the model "Role" contains two records: role_1 and role_2, role_1's content_types
    are set to "dcim.site" and "dcim.device" while the role_2's content_types are set to
    "circuit.circuit" and "dcim.site."

    If Device Model contains a field role, then role_1 is the only Role that is available,
    while role_1 & role_2 are the only Roles that are available for Status.

    The limit_choices_to for the field are automatically derived from:
        - the content-type to which the field is attached (e.g. `dcim.device`)
    """

    def __init__(self, **kwargs):
        kwargs.update(self.set_defaults(**kwargs))
        super().__init__(**kwargs)

    def set_defaults(self, **kwargs):
        """Set defaults of kwargs in class __init__ method.

        Override this method to set __init__ kwargs
        """
        kwargs.setdefault("null", True)

        return kwargs

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
