from django.template import Context

from nautobot.core.ui.breadcrumbs import (
    BaseBreadcrumbItem,
    BreadcrumbItemsType,
    Breadcrumbs,
    InstanceBreadcrumbItem,
    InstanceParentBreadcrumbItem,
    ModelBreadcrumbItem,
)


class RackBreadcrumbs(Breadcrumbs):
    def get_items_for_action(
        self, items: BreadcrumbItemsType, action: str, detail: bool, context: Context
    ) -> list[BaseBreadcrumbItem]:
        if not detail:
            super().get_items_for_action(items, action, detail, context)

        rack = context["object"]
        base_items = [
            ModelBreadcrumbItem(),
            InstanceParentBreadcrumbItem(
                parent_key="location",
            ),
        ]
        detail_item = InstanceBreadcrumbItem()

        if rack.rack_group:
            ancestors_items = [InstanceBreadcrumbItem(instance=ancestor) for ancestor in rack.rack_group.ancestors()]
            return [*base_items, *ancestors_items, InstanceBreadcrumbItem(instance=rack.rack_group), detail_item]

        return [*base_items, detail_item]


class LocationsBreadcrumbs(Breadcrumbs):
    def get_items_for_action(
        self, items: BreadcrumbItemsType, action: str, detail: bool, context: Context
    ) -> list[BaseBreadcrumbItem]:
        if not detail:
            super().get_items_for_action(items, action, detail, context)

        instance = context.get("object")
        ancestors_items = [
            InstanceBreadcrumbItem(instance=ancestor, label=ancestor.name) for ancestor in instance.ancestors()
        ]
        return [ModelBreadcrumbItem(model_key="object"), *ancestors_items, InstanceBreadcrumbItem()]
