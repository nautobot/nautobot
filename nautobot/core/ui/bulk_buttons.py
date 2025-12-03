from nautobot.core.choices import ButtonActionColorChoices
from nautobot.core.ui import object_detail
from nautobot.core.utils.lookup import get_route_for_model


class BaseBulkButton(object_detail.FormButton):
    """Base class for bulk action buttons."""

    action = None
    color = None
    icon = None
    label = None
    weight = None

    def __init__(self, *, form_id: str, model, **kwargs):
        link_name = get_route_for_model(model, f"bulk_{self.action}")

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
    icon = "mdi-rename"
    label = "Rename"
    weight = 200


class BulkEditButton(BaseBulkButton):
    action = "edit"
    color = ButtonActionColorChoices.EDIT
    icon = "mdi-pencil"
    label = "Edit"
    weight = 300


class BulkDisconnectButton(BaseBulkButton):
    action = "disconnect"
    color = ButtonActionColorChoices.DISCONNECT
    icon = "mdi-ethernet-cable-off"
    label = "Disconnect"
    weight = 350


class BulkDeleteButton(BaseBulkButton):
    action = "delete"
    color = ButtonActionColorChoices.DELETE
    icon = "mdi-trash-can-outline"
    label = "Delete"
    weight = 400
