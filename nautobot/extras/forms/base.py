from nautobot.utilities.forms import BootstrapMixin
from .mixins import (
    CustomFieldModelBulkEditFormMixin,
    CustomFieldModelFilterFormMixin,
    CustomFieldModelFormMixin,
    RelationshipModelBulkEditFormMixin,
    RelationshipModelFilterFormMixin,
    RelationshipModelFormMixin,
)


__all__ = (
    "NautobotModelForm",
    "NautobotFilterForm",
    "NautobotBulkEditForm",
)


#
# Nautobot base forms for use in most new custom model forms.
#


class NautobotModelForm(BootstrapMixin, CustomFieldModelFormMixin, RelationshipModelFormMixin):
    """
    This class exists to combine common functionality and is used to inherit from throughout the
    codebase where all three of BootstrapMixin, CustomFieldModelFormMixin and RelationshipModelFormMixin are
    needed.
    """


class NautobotFilterForm(BootstrapMixin, CustomFieldModelFilterFormMixin, RelationshipModelFilterFormMixin):
    """
    This class exists to combine common functionality and is used to inherit from throughout the
    codebase where all three of BootstrapMixin, CustomFieldModelFilterFormMixin and RelationshipModelFilterFormMixin are
    needed.
    """


class NautobotBulkEditForm(BootstrapMixin, CustomFieldModelBulkEditFormMixin, RelationshipModelBulkEditFormMixin):
    """Base class for bulk-edit forms for models that support relationships and custom fields."""
