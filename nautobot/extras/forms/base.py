from nautobot.core.forms import BootstrapMixin

from .mixins import (
    ContactTeamModelFilterFormMixin,
    CustomFieldModelBulkEditFormMixin,
    CustomFieldModelFilterFormMixin,
    CustomFieldModelFormMixin,
    DynamicGroupModelFormMixin,
    NoteModelBulkEditFormMixin,
    NoteModelFormMixin,
    RelationshipModelBulkEditFormMixin,
    RelationshipModelFilterFormMixin,
    RelationshipModelFormMixin,
)

__all__ = (
    "NautobotBulkEditForm",
    "NautobotFilterForm",
    "NautobotModelForm",
)


#
# Nautobot base forms for use in most new custom model forms.
#


class NautobotModelForm(
    BootstrapMixin,
    # The below must be listed *after* BootstrapMixin so that BootstrapMixin applies to their dynamic form fields
    CustomFieldModelFormMixin,
    DynamicGroupModelFormMixin,
    NoteModelFormMixin,
    RelationshipModelFormMixin,
):
    """
    This class exists to combine common functionality and is used to inherit from throughout the
    codebase where all of BootstrapMixin, CustomFieldModelFormMixin, RelationshipModelFormMixin, and
    NoteModelFormMixin are needed.
    """


class NautobotFilterForm(
    BootstrapMixin,
    # The below must be listed *after* BootstrapMixin so that BootstrapMixin applies to their dynamic form fields
    ContactTeamModelFilterFormMixin,
    CustomFieldModelFilterFormMixin,
    RelationshipModelFilterFormMixin,
):
    """
    This class exists to combine common functionality and is used to inherit from throughout the
    codebase where all of ContactTeamModelFilterFormMixin, CustomFieldModelFilterFormMixin, and
    RelationshipModelFilterFormMixin are needed.
    """


class NautobotBulkEditForm(
    BootstrapMixin,
    # The below must be listed *after* BootstrapMixin so that BootstrapMixin applies to their dynamic form fields
    CustomFieldModelBulkEditFormMixin,
    NoteModelBulkEditFormMixin,
    RelationshipModelBulkEditFormMixin,
):
    """Base class for bulk-edit forms for models that support relationships, custom fields and notes."""
