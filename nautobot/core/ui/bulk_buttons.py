from nautobot.core.choices import ButtonActionColorChoices
from nautobot.core.ui import object_detail


class BaseBulkButton(object_detail.FormButton):
    """Base class for bulk action buttons."""

    action = None
    color = None
    icon = None
    label = None
    weight = None

    def __init__(self, *, form_id: str, model, **kwargs):
        model_name = model.__name__.lower()
        app_label = model._meta.app_label
        link_name = f"{app_label}:{model_name}_bulk_{self.action}"

        super().__init__(
            link_name=link_name,
            link_includes_pk=False,
            label=self.label,
            color=self.color,
            icon=self.icon,
            size="xs",
            form_id=form_id,
            weight=self.weight,
            **kwargs,
        )


class BulkRenameButton(BaseBulkButton):
    action = "rename"
    color = ButtonActionColorChoices.RENAME
    icon = "mdi-pencil"
    label = "Rename"
    weight = 200


class BulkEditButton(BaseBulkButton):
    action = "edit"
    color = ButtonActionColorChoices.EDIT
    icon = "mdi-pencil"
    label = "Edit"
    weight = 300


class BulkDeleteButton(BaseBulkButton):
    action = "delete"
    color = ButtonActionColorChoices.DELETE
    icon = "mdi-trash-can-outline"
    label = "Delete"
    weight = 400
