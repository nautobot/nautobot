from nautobot.core.apps import NautobotConfig


class CircuitsConfig(NautobotConfig):
    name = "nautobot.circuits"
    verbose_name = "Circuits"

    def ready(self):
        super().ready()
        import nautobot.circuits.signals  # noqa: F401

    def get_search_types(self):
        from nautobot.circuits.filters import CircuitFilterSet, ProviderFilterSet, ProviderNetworkFilterSet
        from nautobot.circuits.models import Circuit, Provider, ProviderNetwork
        from nautobot.circuits.tables import CircuitTable, ProviderTable, ProviderNetworkTable
        from nautobot.core.utils.utils import count_related

        return {
            "provider": {
                "queryset": Provider.objects.annotate(count_circuits=count_related(Circuit, "provider")),
                "filterset": ProviderFilterSet,
                "table": ProviderTable,
                "url": "circuits:provider_list",
            },
            "circuit": {
                "queryset": Circuit.objects.select_related("type", "provider", "tenant").prefetch_related(
                    "terminations__site"
                ),
                "filterset": CircuitFilterSet,
                "table": CircuitTable,
                "url": "circuits:circuit_list",
            },
            "providernetwork": {
                "queryset": ProviderNetwork.objects.select_related("provider"),
                "filterset": ProviderNetworkFilterSet,
                "table": ProviderNetworkTable,
                "url": "circuits:providernetwork_list",
            },
        }
