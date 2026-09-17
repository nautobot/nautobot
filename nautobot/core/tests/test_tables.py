import contextlib
import importlib
import pkgutil
from types import SimpleNamespace
import warnings

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db import connection
from django.db.models import IntegerField, Value
from django.test import SimpleTestCase, tag, TestCase
from django.test.utils import CaptureQueriesContext
from django_tables2.utils import Accessor

import nautobot
from nautobot.circuits.models import Circuit
from nautobot.circuits.tables import CircuitTable
from nautobot.core.models.querysets import count_related
from nautobot.core.tables import BaseTable, ButtonsColumn, ComputedFieldColumn, LinkedCountColumn
from nautobot.core.templatetags import helpers
from nautobot.dcim.models import Device, InventoryItem, Location, LocationType, Rack, RackGroup
from nautobot.dcim.tables import InventoryItemTable, LocationTable, LocationTypeTable, RackGroupTable
from nautobot.extras.choices import ComputedFieldTypeChoices
from nautobot.extras.models import ComputedField, JobLogEntry
from nautobot.extras.tables import JobLogEntryTable
from nautobot.ipam.models import RIR
from nautobot.ipam.tables import RIRTable
from nautobot.tenancy.tables import TenantGroupTable
from nautobot.wireless.models import WirelessNetwork
from nautobot.wireless.tables import WirelessNetworkTable


class TableTestCase(TestCase):
    maxDiff = None

    def _validate_sorted_tree_queryset_same_with_table_queryset(self, queryset, table_class, field_name):
        with self.subTest(f"Assert sorting {table_class.__name__} on '{field_name}'"):
            table = table_class(queryset.with_tree_fields(), order_by=field_name)
            table_queryset_data = table.data.data.values_list(field_name, flat=True)
            sorted_queryset = (
                queryset.with_tree_fields().extra(order_by=[field_name]).values_list(field_name, flat=True)
            )
            self.assertEqual(list(table_queryset_data), list(sorted_queryset))

        with self.subTest(f"Assert sorting {table_class.__name__} on '-{field_name}'"):
            table = table_class(queryset.with_tree_fields(), order_by=f"-{field_name}")
            table_queryset_data = table.data.data.values_list(field_name, flat=True)
            sorted_queryset = (
                queryset.with_tree_fields().extra(order_by=[f"-{field_name}"]).values_list(field_name, flat=True)
            )
            self.assertEqual(list(table_queryset_data), list(sorted_queryset))

    @tag("example_app")
    def test_tree_model_table_orderable(self):
        """Assert TreeNode model table are orderable."""
        location_type = LocationType.objects.get(name="Campus")
        locations = Location.objects.filter(location_type=location_type)
        devices = Device.objects.all()

        for i in range(3):
            RackGroup.objects.create(name=f"Rack Group {i}", location=locations[i])
            InventoryItem.objects.create(
                device=devices[i], name=f"Inventory Item {i}", manufacturer=devices[i].device_type.manufacturer
            )

        RackGroup.objects.create(
            name="Rack Group 3",
            location=locations[2],
            parent=RackGroup.objects.last(),
        )
        InventoryItem.objects.create(
            name="Inventory Item 3",
            device=devices[3],
            manufacturer=devices[3].device_type.manufacturer,
            parent=InventoryItem.objects.last(),
        )

        tree_node_model_tables = [
            LocationTable,
            LocationTypeTable,
            RackGroupTable,
            InventoryItemTable,
            TenantGroupTable,
        ]

        # Each of the table has at-least two sortable field_names in the field_names
        model_field_names = ["name", "location", "parent", "location_type", "manufacturer"]
        for table_class in tree_node_model_tables:
            queryset = table_class.Meta.model.objects.all()
            table_avail_fields = set(model_field_names) & set(table_class.Meta.fields)
            for table_field_name in table_avail_fields:
                self._validate_sorted_tree_queryset_same_with_table_queryset(queryset, table_class, table_field_name)

        # Test for `rack_count`
        queryset = RackGroupTable.Meta.model.objects.annotate(rack_count=count_related(Rack, "rack_group")).all()
        self._validate_sorted_tree_queryset_same_with_table_queryset(queryset, RackGroupTable, "rack_count")

        # https://github.com/nautobot/nautobot/issues/7330 - sorting by custom field
        l1 = Location.objects.first()
        l1._custom_field_data["example_app_auto_custom_field"] = "alpha"
        l1.validated_save()
        l2 = Location.objects.last()
        l2._custom_field_data["example_app_auto_custom_field"] = "omega"
        l2.validated_save()
        table = LocationTable(
            Location.objects.exclude(_custom_field_data__example_app_auto_custom_field="Default value")
        )

        table.order_by = ["cf_example_app_auto_custom_field"]
        table_queryset_data = table.data.data.values_list("pk", flat=True)
        sorted_queryset = (
            Location.objects.with_tree_fields()
            .exclude(_custom_field_data__example_app_auto_custom_field="Default value")
            .extra(order_by=["_custom_field_data__example_app_auto_custom_field"])
            .values_list("pk", flat=True)
        )
        self.assertEqual(list(table_queryset_data), list(sorted_queryset))

        table.order_by = ["-cf_example_app_auto_custom_field"]
        table_queryset_data = table.data.data.values_list("pk", flat=True)
        sorted_queryset = (
            Location.objects.with_tree_fields()
            .exclude(_custom_field_data__example_app_auto_custom_field="Default value")
            .extra(order_by=["-_custom_field_data__example_app_auto_custom_field"])
            .values_list("pk", flat=True)
        )
        self.assertEqual(list(table_queryset_data), list(sorted_queryset))

    @tag("example_app")
    def test_base_table_apis(self):
        """
        Test BaseTable APIs, specifically visible_columns and configurable_columns.
        Assert that they gave the correct results.
        """
        # Wireless Network Table
        wn_table = WirelessNetworkTable(WirelessNetwork.objects.all(), exclude=["enabled", "hidden"])
        wn_table.columns.hide("description")
        expected_visible_columns = [
            "name",
            "ssid",
            "mode",
            "authentication",
            "actions",
        ]
        expected_configurable_columns = [
            ("name", "Name"),
            ("ssid", "SSID"),
            ("mode", "Mode"),
            ("authentication", "Authentication"),
            ("secrets_group", "Secrets group"),
            ("description", "Description"),
            ("tags", "Tags"),
            ("dynamic_group_count", "Dynamic Groups"),
        ]
        self.assertEqual(wn_table.visible_columns, expected_visible_columns)
        self.assertEqual(wn_table.configurable_columns, expected_configurable_columns)

        # Location Table
        location_table = LocationTable(Location.objects.all(), exclude=["parent", "tenant"])
        location_table.columns.hide("description")
        location_table.columns.hide("tags")
        expected_visible_columns = ["name", "status", "actions"]
        expected_configurable_columns = [
            ("name", "Name"),
            ("status", "Status"),
            ("location_type", "Location type"),
            ("description", "Description"),
            ("facility", "Facility"),
            ("asn", "ASN"),
            ("time_zone", "Time zone"),
            ("physical_address", "Physical address"),
            ("shipping_address", "Shipping address"),
            ("latitude", "Latitude"),
            ("longitude", "Longitude"),
            ("contact_name", "Contact name"),
            ("contact_phone", "Contact phone"),
            ("contact_email", "Contact E-mail"),
            ("tags", "Tags"),
            ("dynamic_group_count", "Dynamic Groups"),
            ("cf_example_app_auto_custom_field", "Example App Automatically Added Custom Field"),
        ]
        self.assertEqual(location_table.visible_columns, expected_visible_columns)
        self.assertEqual(location_table.configurable_columns, expected_configurable_columns)

        # Circuit Table
        circuit_table = CircuitTable(Circuit.objects.all(), exclude=["provider", "circuit_termination_a"])
        circuit_table.columns.hide("tags")
        expected_visible_columns = [
            "cid",
            "circuit_type",
            "status",
            "circuit_termination_z",
            "description",
            "example_app_provider_asn",
            "actions",
        ]
        expected_configurable_columns = [
            ("cid", "ID"),
            ("circuit_type", "Circuit type"),
            ("status", "Status"),
            ("tenant", "Tenant"),
            ("circuit_termination_z", "Side Z"),
            ("install_date", "Date installed"),
            ("commit_rate", "Commit rate (Kbps)"),
            ("description", "Description"),
            ("tags", "Tags"),
            ("example_app_provider_asn", "Provider ASN"),
            ("dynamic_group_count", "Dynamic Groups"),
        ]
        self.assertEqual(circuit_table.visible_columns, expected_visible_columns)
        self.assertEqual(circuit_table.configurable_columns, expected_configurable_columns)

        # Job Log Entry Table (Job Log Entry is not Dynamic Group associable)
        job_log_entry_table = JobLogEntryTable(JobLogEntry.objects.all(), exclude=["created", "message"])
        job_log_entry_table.columns.hide("log_level")
        expected_visible_columns = ["grouping", "log_object"]
        expected_configurable_columns = [
            ("grouping", "Grouping"),
            ("log_level", "Level"),
            ("log_object", "Object"),
        ]
        self.assertEqual(job_log_entry_table.visible_columns, expected_visible_columns)
        self.assertEqual(job_log_entry_table.configurable_columns, expected_configurable_columns)


class BaseTableLinkedCountColumnTestCase(TestCase):
    """Covers the `count_fields` annotation pathway in `BaseTable.__init__`."""

    def test_basetable_construction_is_lazy(self):
        """Constructing a BaseTable around a lazy queryset must not query the DB.

        Querysets are lazy; column setup, annotation chaining, and prefetch
        wiring are pure-Python operations. Any DB query issued here is a sign
        that something forced evaluation of the queryset.
        """
        with CaptureQueriesContext(connection) as ctx:
            RIRTable(RIR.objects.all())
        self.assertEqual(
            len(ctx.captured_queries),
            0,
            f"BaseTable.__init__ issued {len(ctx.captured_queries)} DB queries; "
            "expected 0 because the input queryset is lazy.\n" + "\n".join(q["sql"] for q in ctx.captured_queries),
        )

    def test_annotation_applied_when_missing(self):
        """A LinkedCountColumn's annotation is applied when neither the queryset nor the model has it."""
        table = RIRTable(RIR.objects.all())
        self.assertIn("assigned_prefix_count", table.data.data.query.annotations)

    def test_annotation_preserved_when_already_on_queryset(self):
        """A caller-supplied annotation with the same name as a LinkedCountColumn is preserved, not overwritten."""
        qs = RIR.objects.annotate(assigned_prefix_count=Value(42, output_field=IntegerField()))
        table = RIRTable(qs)
        self.assertIn("assigned_prefix_count", table.data.data.query.annotations)
        row = table.data.data.first()
        if row is not None:
            self.assertEqual(row.assigned_prefix_count, 42)

    def test_annotation_skipped_when_model_defines_attribute(self):
        """The annotation is not applied if the model class already exposes the attribute."""
        RIR.assigned_prefix_count = property(lambda self: 999)
        try:
            table = RIRTable(RIR.objects.all())
            self.assertNotIn("assigned_prefix_count", table.data.data.query.annotations)
        finally:
            del RIR.assigned_prefix_count


class LinkedCountColumnRenderTestCase(TestCase):
    def test_nested_lookup_with_none_mid_chain_falls_back_to_count(self):
        """A None partway through a nested `lookup` chain breaks the walk and falls back to the count badge."""
        column = LinkedCountColumn(
            viewname="dcim:device_list",
            url_params={"ip_addresses": "pk"},
            lookup="interfaces__device__name",
        )
        record = SimpleNamespace(
            pk="00000000-0000-0000-0000-000000000000",
            interfaces_device_name_list=[SimpleNamespace(device=None)],
        )
        rendered = column.render(bound_column=None, record=record, value=1)
        self.assertIn("badge", rendered)


class ButtonsColumnTestCase(TestCase):
    """Covers how ButtonsColumn resolves the `buttons` argument."""

    def test_default_buttons_when_arg_omitted(self):
        """Omitting `buttons` falls back to the class default set."""
        column = ButtonsColumn(RIR)
        self.assertEqual(column.extra_context["buttons"], ButtonsColumn.buttons)

    def test_default_buttons_when_arg_none(self):
        """Passing buttons=None explicitly also falls back to the class default set."""
        column = ButtonsColumn(RIR, buttons=None)
        self.assertEqual(column.extra_context["buttons"], ButtonsColumn.buttons)

    def test_default_buttons_when_buttons_arg_is_missing(self):
        """Missing buttons argument falls back to the class default set."""
        column = ButtonsColumn(RIR)
        self.assertEqual(column.extra_context["buttons"], ButtonsColumn.buttons)

    def test_empty_tuple_means_no_buttons(self):
        """An empty tuple means no buttons, and must not fall back to the defaults."""
        column = ButtonsColumn(RIR, buttons=())
        self.assertEqual(column.extra_context["buttons"], ())

    def test_explicit_subset_is_preserved(self):
        """An explicit non-empty subset is passed through unchanged."""
        column = ButtonsColumn(RIR, buttons=("delete",))
        self.assertEqual(column.extra_context["buttons"], ("delete",))


class ComputedFieldColumnRenderTestCase(TestCase):
    """Covers the content-type guard in `ComputedFieldColumn.render`."""

    @classmethod
    def setUpTestData(cls):
        location_ct = ContentType.objects.get_for_model(Location)
        cls.text_field = ComputedField.objects.create(
            key="cf_render_text",
            label="Computed Field Text",
            template="{{ obj.name }}",
            fallback_value="error",
            content_type=location_ct,
        )
        cls.markdown_field = ComputedField.objects.create(
            key="cf_render_markdown",
            label="Computed Field Markdown",
            template="**{{ obj.name }}**",
            fallback_value="error",
            content_type=location_ct,
        )

    def test_render_evaluates_template_for_matching_row_type(self):
        """A record matching the computed field's content type is rendered via the template."""
        column = ComputedFieldColumn(self.text_field)
        record = Location(name="Matching Location")
        self.assertEqual(column.render(record=record), "Matching Location")

    def test_render_returns_placeholder_for_foreign_row_type(self):
        """A foreign model instance yields the placeholder, not the template output or fallback."""
        column = ComputedFieldColumn(self.text_field)
        # If the guard were missing, the template would render this name instead of a placeholder.
        record = LocationType(name="Should Not Render")
        self.assertEqual(column.render(record=record), helpers.placeholder(None))

    def test_render_returns_placeholder_for_non_model_row(self):
        """`available`-style rows (not model instances at all) also skip template evaluation."""
        column = ComputedFieldColumn(self.text_field)
        record = SimpleNamespace(name="Should Not Render")
        self.assertEqual(column.render(record=record), helpers.placeholder(None))

    def test_render_applies_markdown_output_type_for_matching_row(self):
        """Markdown computed fields still pass through the markdown renderer for matching rows."""
        self.markdown_field.output_type = ComputedFieldTypeChoices.TYPE_MARKDOWN
        column = ComputedFieldColumn(self.markdown_field)
        record = Location(name="Bold")
        self.assertEqual(column.render(record=record), helpers.render_markdown("**Bold**"))


def _all_subclasses(cls):
    """Every subclass of `cls`, recursively."""
    subclasses = set()
    for subclass in cls.__subclasses__():
        subclasses.add(subclass)
        subclasses |= _all_subclasses(subclass)
    return subclasses


def _import_all_table_modules():
    """Import every `tables` module under `nautobot` so all `BaseTable` subclasses are registered."""
    for module_info in pkgutil.walk_packages(nautobot.__path__, f"{nautobot.__name__}."):
        if ".tables" not in module_info.name and not module_info.name.endswith("tables"):
            continue
        with contextlib.suppress(Exception):
            # Some optional/app modules aren't importable in every configuration; skipping them
            # only narrows coverage, and the assertion below is about what *is* importable.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                importlib.import_module(module_info.name)


class TableAccessorAuditTestCase(SimpleTestCase):
    """Static audit of every table column accessor, whether declared or derived from the column name.

    Pure introspection, no database access.
    Regression test for nautobot#9341.
    """

    def test_no_accessor_traverses_a_to_many_relation(self):
        """No column accessor may traverse a to-many relation and then keep going.

        `Accessor.resolve()` walks Python attributes, so a to-many relation yields a related manager,
        which has none of the target model's attributes. Any further path segment therefore raises,
        and `BoundRow._get_and_render_with` swallows the exception and renders the column default.
        The column silently degrades to a placeholder at HTTP 200, which is exactly how nautobot#9341
        shipped undetected past the list-view test suite.
        """
        _import_all_table_modules()
        violations = []
        for table in _all_subclasses(BaseTable):
            model = getattr(table._meta, "model", None)
            if model is None:
                continue
            for name, column in table.base_columns.items():
                accessor = column.accessor if column.accessor is not None else name
                bits = str(accessor).split(Accessor.SEPARATOR)
                current = model
                for index, bit in enumerate(bits):
                    if current is None:
                        break
                    try:
                        field = current._meta.get_field(bit)
                    except (FieldDoesNotExist, AttributeError):
                        break  # a property or method: not statically decidable, so leave it alone
                    if field.one_to_many or field.many_to_many:
                        if index < len(bits) - 1:
                            violations.append(f"{table.__module__}.{table.__name__}.{name} -> {accessor}")
                        break
                    if isinstance(field, GenericForeignKey):
                        break  # resolves to a single object, but its model isn't knowable statically
                    current = getattr(getattr(field, "remote_field", None), "model", None)
        self.assertEqual(
            sorted(violations),
            [],
            "These accessors traverse a to-many relation (a manager) and will render as placeholders. "
            "Route them through a property that returns a single object instead.",
        )
