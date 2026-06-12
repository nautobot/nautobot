"""Tests for the Bulk Connect cable-creation service (nautobot.dcim.cables.bulk_connect)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from nautobot.core.testing import TestCase
from nautobot.dcim.cables import (
    BulkCableConnectService,
    BulkConnectSpec,
    ConnectorSelection,
    walk_terminations,
)
from nautobot.dcim.models import (
    Cable,
    CableToCableTermination,
    CableType,
    Device,
    DeviceType,
    Interface,
    Location,
    Manufacturer,
)
from nautobot.extras.models import Role, Status

User = get_user_model()


class _BulkConnectFixture:
    """Shared device/interface fixture + spec helpers for the bulk-connect test classes."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        location = Location.objects.first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Bulk Connect DT")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        interface_status = Status.objects.get_for_model(Interface).first()

        cls.panel_a = Device.objects.create(
            device_type=device_type, role=device_role, name="PanelA", location=location, status=device_status
        )
        cls.panel_b = Device.objects.create(
            device_type=device_type, role=device_role, name="PanelB", location=location, status=device_status
        )
        # 12 physical interfaces per panel, named so the naturalized ordering is eth0..eth11.
        cls.a = [
            Interface.objects.create(device=cls.panel_a, name=f"eth{i}", status=interface_status, type="1000base-t")
            for i in range(12)
        ]
        cls.b = [
            Interface.objects.create(device=cls.panel_b, name=f"eth{i}", status=interface_status, type="1000base-t")
            for i in range(12)
        ]
        cls.cable_status = Status.objects.get_for_model(Cable).get(name="Connected")
        cls.breakout_1x4 = CableType.objects.create(name="BC 1x4", a_connectors=1, b_connectors=4, total_lanes=4)
        cls.bulk_user = User.objects.create_superuser(username="bulk_connect_su", email="su@example.com", password="pw")

    # -- helpers --

    def _sel(self, side, connector, termination):
        return ConnectorSelection(side=side, connector=connector, termination=termination)

    def _spec(self, *, cable_type=None, selections, count, **kwargs):
        return BulkConnectSpec(
            cable_type=cable_type,
            selections=selections,
            count=count,
            status=kwargs.pop("status", self.cable_status),
            **kwargs,
        )

    def _service(self, spec, *, user=None):
        """Build the service with a permitted user by default (``user`` is now required)."""
        return BulkCableConnectService(spec, user=user or self.bulk_user)


class BulkConnectServiceTestCase(_BulkConnectFixture, TestCase):
    """Unit tests for the walk, resolve, validate, and create steps of the service."""

    # -- walk --

    def test_walk_forward_from_start(self):
        self.assertEqual(walk_terminations(self.a[2], 3), [self.a[2], self.a[3], self.a[4]])

    def test_walk_count_one(self):
        self.assertEqual(walk_terminations(self.a[5], 1), [self.a[5]])

    def test_walk_overshoot_fills_to_end(self):
        # Only 2 terminations remain from eth10 (eth10, eth11); a larger count stops there.
        self.assertEqual(walk_terminations(self.a[10], 5), [self.a[10], self.a[11]])

    def test_walk_skips_connected(self):
        # Connect eth1; the walk from eth0 should skip it and continue to the next open ports.
        Cable(termination_a=self.a[1], termination_b=self.b[11], status=self.cable_status).save()
        self.assertEqual(walk_terminations(self.a[0], 3), [self.a[0], self.a[2], self.a[3]])

    # -- resolve --

    def test_resolve_non_breakout_blocks(self):
        spec = self._spec(
            selections=[self._sel("A", 1, self.a[0]), self._sel("B", 1, self.b[0])],
            count=4,
        )
        resolved = self._service(spec).resolve()
        self.assertEqual(resolved["A"].terminations, self.a[0:4])
        self.assertEqual(resolved["B"].terminations, self.b[0:4])
        self.assertEqual(resolved["A"].filled_cables, 4)

    def test_resolve_a_sel_2(self):
        # The reviewer's example: 2 connectors selected, count=3 -> 6 A terminations (2 selected + 4 walked).
        spec = self._spec(
            cable_type=CableType.objects.create(name="BC 2x4", a_connectors=2, b_connectors=4, total_lanes=4),
            selections=[self._sel("A", 1, self.a[0]), self._sel("A", 2, self.a[1])],
            count=3,
        )
        resolved = self._service(spec).resolve()
        self.assertEqual(resolved["A"].terminations, self.a[0:6])
        self.assertEqual(resolved["A"].sel, 2)
        self.assertEqual([resolved["A"].block(i) for i in range(3)], [self.a[0:2], self.a[2:4], self.a[4:6]])

    # -- create: non-breakout --

    def test_create_non_breakout_makes_n_cables(self):
        spec = self._spec(
            selections=[self._sel("A", 1, self.a[0]), self._sel("B", 1, self.b[0])],
            count=4,
        )
        result = self._service(spec).run()
        self.assertEqual(len(result.cables), 4)
        self.assertFalse(result.is_breakout)
        for i, cable in enumerate(result.cables):
            self.assertEqual(cable.termination_a, self.a[i])
            self.assertEqual(cable.termination_b, self.b[i])

    def test_count_one_single_cable(self):
        spec = self._spec(
            selections=[self._sel("A", 1, self.a[7]), self._sel("B", 1, self.b[7])],
            count=1,
        )
        result = self._service(spec).run()
        self.assertEqual(len(result.cables), 1)
        self.assertEqual(result.cables[0].termination_a, self.a[7])

    def test_per_cable_label_suffix(self):
        spec = self._spec(
            selections=[self._sel("A", 1, self.a[0]), self._sel("B", 1, self.b[0])],
            count=3,
            label="trunk",
        )
        result = self._service(spec).run()
        self.assertEqual([c.label for c in result.cables], ["trunk (1)", "trunk (2)", "trunk (3)"])

    # -- create: breakout --

    def test_create_breakout_partial(self):
        # a_sel=1, b_sel=1 on a 1x4 type, count=3 -> 3 cables each using only connector 1.
        spec = self._spec(
            cable_type=self.breakout_1x4,
            selections=[self._sel("A", 1, self.a[0]), self._sel("B", 1, self.b[0])],
            count=3,
        )
        result = self._service(spec).run()
        self.assertEqual(len(result.cables), 3)
        self.assertTrue(result.is_breakout)
        for i, cable in enumerate(result.cables):
            self.assertEqual([t.termination for t in cable.terminations_a], [self.a[i]])
            self.assertEqual([t.termination for t in cable.terminations_b], [self.b[i]])

    def test_create_breakout_full(self):
        # a_sel=1, b_sel=4, count=3 -> 3 cables, each A.ethX <-> 4 consecutive B interfaces.
        spec = self._spec(
            cable_type=self.breakout_1x4,
            selections=[
                self._sel("A", 1, self.a[0]),
                self._sel("B", 1, self.b[0]),
                self._sel("B", 2, self.b[1]),
                self._sel("B", 3, self.b[2]),
                self._sel("B", 4, self.b[3]),
            ],
            count=3,
        )
        result = self._service(spec).run()
        self.assertEqual(len(result.cables), 3)
        self.assertEqual([t.termination for t in result.cables[0].terminations_b], self.b[0:4])
        self.assertEqual([t.termination for t in result.cables[1].terminations_b], self.b[4:8])
        self.assertEqual([t.termination for t in result.cables[2].terminations_b], self.b[8:12])

    # -- validation / aborts --

    def test_abort_uneven_creates_nothing(self):
        before = Cable.objects.count()
        spec = self._spec(
            selections=[self._sel("A", 1, self.a[0]), self._sel("B", 1, self.b[0])],
            count=100,  # only 12 available per side
        )
        with self.assertRaises(ValidationError):
            self._service(spec).run()
        self.assertEqual(Cable.objects.count(), before)
        self.assertFalse(CableToCableTermination.objects.filter(interface__in=self.a).exists())

    def test_create_skips_connected_terminations(self):
        # a[2] is already cabled; the walk from a[0] should skip it (use a[0], a[1], a[3]).
        Cable(termination_a=self.a[2], termination_b=self.b[11], status=self.cable_status).save()
        spec = self._spec(
            selections=[self._sel("A", 1, self.a[0]), self._sel("B", 1, self.b[0])],
            count=3,
        )
        result = self._service(spec).run()
        self.assertEqual([c.termination_a for c in result.cables], [self.a[0], self.a[1], self.a[3]])
        self.assertEqual([c.termination_b for c in result.cables], [self.b[0], self.b[1], self.b[2]])

    def test_abort_length_without_unit(self):
        # Length-without-unit is enforced by Cable.clean() during the atomic create (not re-checked in
        # the service), so it raises on run() and rolls back, creating nothing.
        before = Cable.objects.count()
        spec = self._spec(
            selections=[self._sel("A", 1, self.a[0]), self._sel("B", 1, self.b[0])],
            count=2,
            length=5,
        )
        with self.assertRaises(ValidationError):
            self._service(spec).run()
        self.assertEqual(Cable.objects.count(), before)

    def test_permission_denied_without_add_cable(self):
        user = User.objects.create_user(username="noperm")
        spec = self._spec(
            selections=[self._sel("A", 1, self.a[0]), self._sel("B", 1, self.b[0])],
            count=2,
        )
        service = BulkCableConnectService(spec, user=user)
        with self.assertRaises(ValidationError):
            service.validate(service.resolve())


class BulkConnectFormTestCase(_BulkConnectFixture, TestCase):
    """Exercises the CableCreateForm + its Count field on the cable add form."""

    def _post_data(self, **overrides):
        from nautobot.dcim.forms import CableCreateForm

        data = {
            "a_conn_1_type": "interface",
            "a_conn_1_parent": self.panel_a.pk,
            "a_conn_1_termination": self.a[0].pk,
            "b_conn_1_type": "interface",
            "b_conn_1_parent": self.panel_b.pk,
            "b_conn_1_termination": self.b[0].pk,
            "status": self.cable_status.pk,
            "count": 1,
        }
        data.update(overrides)
        return CableCreateForm(data=data)

    def test_form_has_optional_count_field(self):
        field = self._post_data().fields["count"]
        self.assertFalse(field.required)
        self.assertEqual(field.min_value, 2)

    def test_form_valid_without_count(self):
        form = self._post_data()  # count=1 -> below min, but field is optional; treat blank
        # A single-cable submission leaves count blank.
        form = self._post_data(count="")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data.get("count"))

    def test_form_count_below_minimum_invalid(self):
        form = self._post_data(count=1)
        self.assertFalse(form.is_valid())
        self.assertIn("count", form.errors)


class BulkConnectViewTestCase(_BulkConnectFixture, TestCase):
    """Exercises the cable add view's three submission intents (create / bulk add / confirm)."""

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()

    def _data(self, **overrides):
        data = {
            "a_conn_1_type": "interface",
            "a_conn_1_parent": self.panel_a.pk,
            "a_conn_1_termination": self.a[0].pk,
            "b_conn_1_type": "interface",
            "b_conn_1_parent": self.panel_b.pk,
            "b_conn_1_termination": self.b[0].pk,
            "status": self.cable_status.pk,
        }
        data.update(overrides)
        return data

    def test_single_create_with_count_rejected(self):
        from django.urls import reverse

        before = Cable.objects.count()
        response = self.client.post(reverse("dcim:cable_add"), self._data(count=3, _create=""))
        self.assertEqual(response.status_code, 200)  # re-rendered with error
        self.assertEqual(Cable.objects.count(), before)

    def test_bulk_add_without_count_rejected(self):
        from django.urls import reverse

        before = Cable.objects.count()
        response = self.client.post(reverse("dcim:cable_bulk_connect"), self._data(_bulkadd=""))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Cable.objects.count(), before)

    def test_bulk_add_renders_confirmation_without_creating(self):
        from django.urls import reverse

        before = Cable.objects.count()
        response = self.client.post(
            reverse("dcim:cable_bulk_connect"), self._data(count=3, label="my-trunk", _bulkadd="")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Cable.objects.count(), before)  # nothing created yet
        self.assertContains(response, "Create 3 cables")
        # The submitted attribute values must carry into the read-only confirmation view.
        self.assertContains(response, "my-trunk")

    def test_bulk_confirm_creates_n_cables(self):
        from django.urls import reverse

        before = Cable.objects.count()
        response = self.client.post(reverse("dcim:cable_bulk_connect"), self._data(count=3, _bulkconfirm=""))
        self.assertEqual(response.status_code, 302, getattr(response, "content", b"")[:500])
        self.assertEqual(Cable.objects.count(), before + 3)

    def test_lane_fill_populates_connectors(self):
        from django.urls import reverse

        # 1x4 breakout: fill the B side from connector 1 -> connectors 2-4 get the next open ports.
        response = self.client.get(
            reverse("dcim:cable_lane_fill"),
            {
                "cable_type": self.breakout_1x4.pk,
                "fill_side": "b",
                "b_conn_1_type": "interface",
                "b_conn_1_parent": self.panel_b.pk,
                "b_conn_1_termination": str(self.b[0].pk),
            },
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(str(self.b[1].pk), content)
        self.assertIn(str(self.b[3].pk), content)
