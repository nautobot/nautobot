from django.contrib.contenttypes.models import ContentType

from nautobot.circuits.choices import CircuitTerminationSideChoices
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.cloud.models import CloudAccount, CloudNetwork, CloudResourceType
from nautobot.cloud.tables import CloudNetworkTable
from nautobot.core.testing import AssertNoRepeatedQueries, TestCase
from nautobot.extras.models import Status


class CloudNetworkTableTestCase(TestCase):
    """Assert the Circuits column renders the circuit ID for a single circuit and a count otherwise."""

    @classmethod
    def setUpTestData(cls):
        cloud_network_ct = ContentType.objects.get_for_model(CloudNetwork)
        cloud_resource_type = CloudResourceType.objects.get_for_model(CloudNetwork).first()
        cloud_resource_type.content_types.add(cloud_network_ct)
        cloud_account = CloudAccount.objects.first()

        def _make_network(name):
            return CloudNetwork.objects.create(
                name=name, cloud_resource_type=cloud_resource_type, cloud_account=cloud_account
            )

        cls.network_single = _make_network("CloudNetworkTable Network Single")
        cls.network_multiple = _make_network("CloudNetworkTable Network Multiple")
        cls.network_double_termination = _make_network("CloudNetworkTable Network Double Termination")
        cls.network_empty = _make_network("CloudNetworkTable Network Empty")

        provider = Provider.objects.first()
        circuit_type = CircuitType.objects.first()
        circuit_status = Status.objects.get_for_model(Circuit).first()

        def _make_circuit(cid):
            return Circuit.objects.create(cid=cid, provider=provider, circuit_type=circuit_type, status=circuit_status)

        # One circuit terminating on the single network.
        cls.circuit_1 = _make_circuit("CloudNetworkTable Circuit 1")
        CircuitTermination.objects.create(
            circuit=cls.circuit_1, term_side=CircuitTerminationSideChoices.SIDE_A, cloud_network=cls.network_single
        )

        # Two distinct circuits terminating on the multiple network.
        cls.circuit_2 = _make_circuit("CloudNetworkTable Circuit 2")
        cls.circuit_3 = _make_circuit("CloudNetworkTable Circuit 3")
        CircuitTermination.objects.create(
            circuit=cls.circuit_2, term_side=CircuitTerminationSideChoices.SIDE_A, cloud_network=cls.network_multiple
        )
        CircuitTermination.objects.create(
            circuit=cls.circuit_3, term_side=CircuitTerminationSideChoices.SIDE_A, cloud_network=cls.network_multiple
        )

        # A single circuit with BOTH terminations on the same network: distinct=True keeps this at one circuit.
        cls.circuit_4 = _make_circuit("CloudNetworkTable Circuit 4")
        CircuitTermination.objects.create(
            circuit=cls.circuit_4,
            term_side=CircuitTerminationSideChoices.SIDE_A,
            cloud_network=cls.network_double_termination,
        )
        CircuitTermination.objects.create(
            circuit=cls.circuit_4,
            term_side=CircuitTerminationSideChoices.SIDE_Z,
            cloud_network=cls.network_double_termination,
        )

    def _render_cell(self, cloud_network, column_name):
        table = CloudNetworkTable(CloudNetwork.objects.filter(pk=cloud_network.pk))
        bound_row = table.rows[0]
        return bound_row.get_cell(column_name)  # pylint: disable=no-member

    def test_single_circuit_shows_cid(self):
        cell = self._render_cell(self.network_single, "circuit_count")
        self.assertIn(self.circuit_1.cid, cell)
        self.assertNotIn("badge", cell)

    def test_multiple_circuits_shows_count(self):
        cell = self._render_cell(self.network_multiple, "circuit_count")
        self.assertIn('class="badge bg-primary">2</a>', cell)

    def test_single_circuit_with_two_terminations_shows_cid(self):
        # distinct=True -> one distinct circuit -> render the circuit ID, not a "2" badge.
        cell = self._render_cell(self.network_double_termination, "circuit_count")
        self.assertIn(self.circuit_4.cid, cell)
        self.assertNotIn("badge", cell)

    def test_no_circuits_shows_placeholder(self):
        cell = self._render_cell(self.network_empty, "circuit_count")
        self.assertNotIn("badge", cell)
        self.assertNotIn("/circuits/circuits/", cell)

    def test_circuit_column_avoids_n_plus_one_queries(self):
        """The Circuits column must render without per-row queries.

        The single-circuit display relies on a prefetch whose queryset `select_related`s `circuit`. If that
        select_related is ever dropped, accessing `.circuit` would fall back to one query per row. Render
        enough single-circuit rows that such a regression would trip `AssertNoRepeatedQueries`.
        """
        # Add cloud networks, each with its own single circuit, so the table has well more rows than the
        # N+1 threshold.
        for i in range(15):
            network = CloudNetwork.objects.create(
                name=f"CloudNetworkTable Network Extra {i}",
                cloud_resource_type=self.network_single.cloud_resource_type,
                cloud_account=self.network_single.cloud_account,
            )
            circuit = Circuit.objects.create(
                cid=f"CloudNetworkTable Extra Circuit {i}",
                provider=self.circuit_1.provider,
                circuit_type=self.circuit_1.circuit_type,
                status=self.circuit_1.status,
            )
            CircuitTermination.objects.create(
                circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_A, cloud_network=network
            )

        with AssertNoRepeatedQueries(self):
            table = CloudNetworkTable(CloudNetwork.objects.filter(name__startswith="CloudNetworkTable Network"))
            for row in table.rows:
                row.get_cell("circuit_count")  # pylint: disable=no-member
