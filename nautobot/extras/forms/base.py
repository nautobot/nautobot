from nautobot.utilities.forms import BootstrapMixin
from .mixins import (
    CustomFieldBulkEditForm,
    CustomFieldModelForm,
    CustomFieldFilterForm,
    NoteModelBulkEditFormMixin,
    NoteModelFormMixin,
    RelationshipModelBulkEditFormMixin,
    RelationshipModelFormMixin,
    RelationshipModelFilterFormMixin,
)


__all__ = (
    "NautobotModelForm",
    "NautobotFilterForm",
    "NautobotBulkEditForm",
)


#
# Nautobot base forms for use in most new custom model forms.
#


class NautobotModelForm(BootstrapMixin, CustomFieldModelForm, RelationshipModelFormMixin, NoteModelFormMixin):
    """
    This class exists to combine common functionality and is used to inherit from throughout the
    codebase where all of BootstrapMixin, CustomFieldModelForm, RelationshipModelForm and NoteModelForm are
    needed.
    """


class NautobotFilterForm(BootstrapMixin, CustomFieldFilterForm, RelationshipModelFilterFormMixin):
    """
    This class exists to combine common functionality and is used to inherit from throughout the
    codebase where all three of BootstrapMixin, CustomFieldFilterForm and RelationshipModelFilterForm are
    needed.
    """


class NautobotBulkEditForm(
    BootstrapMixin, CustomFieldBulkEditForm, RelationshipModelBulkEditFormMixin, NoteModelBulkEditFormMixin
):
    """Base class for bulk-edit forms for models that support relationships, custom fields and notes."""
