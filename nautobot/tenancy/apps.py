from nautobot.core.apps import NautobotConfig


class TenancyConfig(NautobotConfig):
    name = "nautobot.tenancy"

    def get_search_types(self):
        from nautobot.tenancy.filters import TenantFilterSet
        from nautobot.tenancy.models import Tenant
        from nautobot.tenancy.tables import TenantTable

        return {
            "tenant": {
                "queryset": Tenant.objects.select_related("group"),
                "filterset": TenantFilterSet,
                "table": TenantTable,
                "url": "tenancy:tenant_list",
            },
        }
