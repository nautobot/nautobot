import uuid

from nautobot.circuits.models import Circuit, CircuitType, Provider
from nautobot.core.testing.integration import (
    BulkOperationsTestCases,
)
from nautobot.extras.models import Status


class CircuitBulkOperationsTestCase(BulkOperationsTestCases.BulkOperationsTestCase):
    """
    Test circuits bulk edit / delete operations.
    """

    model_menu_path = ("Circuits", "Circuits")
    model_base_viewname = "circuits:circuit"
    model_edit_data = {"commit_rate": "12345"}
    model_filter_by = {"circuit_type": "Copper"}
    model_class = Circuit

    def setup_items(self):
        Circuit.objects.all().delete()

        # Create locations for test
        self.create_circuit()
        self.create_circuit()
        self.create_circuit()
        self.create_circuit("Copper")
        self.create_circuit("Copper")

    @staticmethod
    def create_circuit(circuit_type="Fiber"):
        circuit_id = f"TestCircuit-{str(uuid.uuid4())[:6]}"
        provider, _ = Provider.objects.get_or_create(name="A Test Provider")
        circuit_type, _ = CircuitType.objects.get_or_create(name=circuit_type)

        circuit_status = Status.objects.get_for_model(Circuit).first()
        Circuit.objects.get_or_create(
            cid=circuit_id,
            provider=provider,
            status=circuit_status,
            circuit_type=circuit_type,
        )
