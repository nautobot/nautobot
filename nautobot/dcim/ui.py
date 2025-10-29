from django.template import Context

from nautobot.core.ui.breadcrumbs import (
    AncestorsBreadcrumbs,
    InstanceBreadcrumbItem,
    InstanceParentBreadcrumbItem,
    ModelBreadcrumbItem,
)
from nautobot.core.views.utils import get_obj_from_context
from nautobot.dcim.models import Rack


class RackBreadcrumbs(AncestorsBreadcrumbs):
    def get_detail_items(self, context: Context):
        rack: Rack = get_obj_from_context(context)
        base_items = [
            ModelBreadcrumbItem(),
            InstanceParentBreadcrumbItem(
                parent_key="location",
                label=rack.location.page_title,
            ),
        ]
        if rack.rack_group:
            ancestors_items = self.get_ancestors_items(rack.rack_group)
            return [*base_items, *ancestors_items, InstanceBreadcrumbItem(instance=rack.rack_group)]

        return base_items
