from nautobot.circuits.models import Circuit, Provider
from nautobot.core.apps import HomePageItem, HomePagePanel


layout = (
    HomePagePanel(
        name="Circuits",
        weight=500,
        items=(
            HomePageItem(
                name="Providers",
                link="circuits:provider_list",
                model=Provider,
                description="Organizations which provide circuit connectivity",
                permissions=["circuits.view_provider"],
                weight=100,
            ),
            HomePageItem(
                name="Circuits",
                link="circuits:circuit_list",
                model=Circuit,
                description="Communication links for Internet transit, peering, and other services",
                permissions=["circuits.view_circuit"],
                weight=200,
            ),
        ),
    ),
)
