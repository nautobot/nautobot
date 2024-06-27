from nautobot.core.forms import BootstrapMixin

from .mixins import (
    ContactTeamModelFilterFormMixin,
    CustomFieldModelBulkEditFormMixin,
    CustomFieldModelFilterFormMixin,
    CustomFieldModelFormMixin,
    NoteModelBulkEditFormMixin,
    NoteModelFormMixin,
    RelationshipModelBulkEditFormMixin,
    RelationshipModelFilterFormMixin,
    RelationshipModelFormMixin,
    StaticGroupModelFormMixin,
)

__all__ = (
    "NautobotModelForm",
    "NautobotFilterForm",
    "NautobotBulkEditForm",
)


#
# Nautobot base forms for use in most new custom model forms.
#


class NautobotModelForm(
    CustomFieldModelFormMixin,
    NoteModelFormMixin,
    RelationshipModelFormMixin,
    StaticGroupModelFormMixin,
    BootstrapMixin,
):
    """
    This class exists to combine common functionality and is used to inherit from throughout the
    codebase where all of BootstrapMixin, CustomFieldModelFormMixin, RelationshipModelFormMixin, and
    NoteModelFormMixin are needed.
    """


class NautobotFilterForm(
    ContactTeamModelFilterFormMixin,
    BootstrapMixin,
    CustomFieldModelFilterFormMixin,  # currently must come *after* BootstrapMixin to get proper CSS classes applied
    RelationshipModelFilterFormMixin,
):
    """
    This class exists to combine common functionality and is used to inherit from throughout the
    codebase where all of ContactTeamModelFilterFormMixin, CustomFieldModelFilterFormMixin, and
    RelationshipModelFilterFormMixin are needed.
    """


class NautobotBulkEditForm(
    BootstrapMixin, CustomFieldModelBulkEditFormMixin, RelationshipModelBulkEditFormMixin, NoteModelBulkEditFormMixin
):
    """Base class for bulk-edit forms for models that support relationships, custom fields and notes."""
