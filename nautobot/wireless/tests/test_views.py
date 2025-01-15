import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.test import override_settings
from tree_queries.models import TreeNode

from nautobot.core.testing import utils, ViewTestCases
from nautobot.core.utils import lookup
from nautobot.dcim.models import Controller, ControllerManagedDeviceGroup
from nautobot.extras import choices as extras_choices
from nautobot.extras.models import SecretsGroup, Tag
from nautobot.users import models as users_models
from nautobot.wireless import choices
from nautobot.wireless.models import RadioProfile, SupportedDataRate, WirelessNetwork


class WirelessNetworkTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = WirelessNetwork

    @classmethod
    def setUpTestData(cls):
        cls.wireless_network = WirelessNetwork.objects.create(
            name="Deletable Wireless Network 1",
            mode=choices.WirelessNetworkModeChoices.STANDALONE,
            authentication=choices.WirelessNetworkAuthenticationChoices.WPA2_PERSONAL,
            ssid="SSID 1",
            description="Description 1",
            enabled=True,
            hidden=False,
            secrets_group=SecretsGroup.objects.first(),
        )
        WirelessNetwork.objects.create(
            name="Deletable Wireless Network 2",
            mode=choices.WirelessNetworkModeChoices.CENTRAL,
            authentication=choices.WirelessNetworkAuthenticationChoices.WPA2_ENTERPRISE,
            ssid="SSID 2",
            description="Description 2",
            enabled=True,
            hidden=False,
            secrets_group=SecretsGroup.objects.first(),
        )
        WirelessNetwork.objects.create(
            name="Deletable Wireless Network 3",
            mode=choices.WirelessNetworkModeChoices.LOCAL,
            authentication=choices.WirelessNetworkAuthenticationChoices.WPA2_ENTERPRISE,
            ssid="SSID 3",
            description="Description 3",
            enabled=False,
            hidden=True,
            secrets_group=SecretsGroup.objects.first(),
        )
        cls.form_data = {
            "name": "New Wireless Network",
            "description": "A new wireless network",
            "mode": choices.WirelessNetworkModeChoices.MESH,
            "authentication": choices.WirelessNetworkAuthenticationChoices.WPA3_ENTERPRISE_192_BIT,
            "ssid": "SOME SSID",
            "tags": [t.pk for t in Tag.objects.get_for_model(WirelessNetwork)],
            # Management form fields required for the dynamic Controller Managed Device Group formset
            "controller_managed_device_group_assignments-TOTAL_FORMS": "0",
            "controller_managed_device_group_assignments-INITIAL_FORMS": "1",
            "controller_managed_device_group_assignments-MIN_NUM_FORMS": "0",
            "controller_managed_device_group_assignments-MAX_NUM_FORMS": "1000",
        }

        cls.bulk_edit_data = {
            "mode": choices.WirelessNetworkModeChoices.LOCAL,
            "authentication": choices.WirelessNetworkAuthenticationChoices.WPA2_ENTERPRISE,
            "enabled": False,
            "ssid": "New SSID",
            "description": "New description",
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_with_controled_manged_device_group_vlan_set_to_none(self):
        """Assert bug report #6763 (Wireless Network tab fails to render under Controller View) has been resolved"""
        instance = self.wireless_network

        controller = Controller.objects.first()
        cmdg = ControllerManagedDeviceGroup.objects.create(
            name="Test ControllerManagedDeviceGroup",
            controller=controller,
        )
        cmdg.wireless_networks.add(instance)

        self.add_permissions(
            "wireless.view_wirelessnetwork", "wireless.view_controllermanageddevicegroupwirelessnetworkassignment"
        )

        # Try GET with model-level permission
        response = self.client.get(instance.get_absolute_url())
        self.assertInHTML("Test ControllerManagedDeviceGroup", response.content.decode(response.charset))


class SupportedDataRateTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = SupportedDataRate

    @classmethod
    def setUpTestData(cls):
        # Use high rate values that won't conflict with the factory rates
        SupportedDataRate.objects.create(rate=165000, standard=choices.SupportedDataRateStandardChoices.B, mcs_index=1)
        SupportedDataRate.objects.create(rate=169000, standard=choices.SupportedDataRateStandardChoices.G, mcs_index=2)
        SupportedDataRate.objects.create(rate=280000, standard=choices.SupportedDataRateStandardChoices.N, mcs_index=3)
        cls.form_data = {
            "rate": 300000,
            "standard": "802.11ac",
            "tags": [t.pk for t in Tag.objects.get_for_model(SupportedDataRate)],
        }
        cls.bulk_edit_data = {
            "mcs_index": 11,
        }


class RadioProfileTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = RadioProfile

    @classmethod
    def setUpTestData(cls):
        supported_data_rates = (
            SupportedDataRate.objects.create(
                rate=1000000, standard=choices.SupportedDataRateStandardChoices.AC, mcs_index=1
            ),
            SupportedDataRate.objects.create(
                rate=600000, standard=choices.SupportedDataRateStandardChoices.AX, mcs_index=2
            ),
            SupportedDataRate.objects.create(
                rate=1280000, standard=choices.SupportedDataRateStandardChoices.BE, mcs_index=3
            ),
        )
        rp1 = RadioProfile.objects.create(
            name="Deletable Radio Profile 1",
            frequency=choices.RadioProfileFrequencyChoices.FREQUENCY_5G,
            tx_power_min=1,
            tx_power_max=10,
            channel_width=[20, 40, 80],
            allowed_channel_list=[36, 40, 44, 48],
            regulatory_domain=choices.RadioProfileRegulatoryDomainChoices.US,
            rx_power_min=-90,
        )
        rp2 = RadioProfile.objects.create(
            name="Deletable Radio Profile 2",
            frequency=choices.RadioProfileFrequencyChoices.FREQUENCY_2_4G,
            tx_power_min=2,
            tx_power_max=11,
            channel_width=[20, 40, 80, 160],
            allowed_channel_list=[1, 6, 11],
            regulatory_domain=choices.RadioProfileRegulatoryDomainChoices.JP,
            rx_power_min=-89,
        )
        rp3 = RadioProfile.objects.create(
            name="Deletable Radio Profile 3",
            frequency=choices.RadioProfileFrequencyChoices.FREQUENCY_6G,
            tx_power_min=15,
            tx_power_max=25,
            rx_power_min=-80,
            regulatory_domain=choices.RadioProfileRegulatoryDomainChoices.JP,
            allowed_channel_list=[],
            channel_width=[],
        )
        rp1.supported_data_rates.set([supported_data_rates[0]])
        rp2.supported_data_rates.set([supported_data_rates[1]])
        rp3.supported_data_rates.set(supported_data_rates[:2])
        cls.form_data = {
            "name": "New Radio Profile",
            "frequency": choices.RadioProfileFrequencyChoices.FREQUENCY_5G,
            "tx_power_min": 1,
            "tx_power_max": 10,
            "allowed_channel_list": "1,6,11,36,161,165",
            "channel_width": [20, 40],
            "regulatory_domain": choices.RadioProfileRegulatoryDomainChoices.US,
            "rx_power_min": -90,
            "tags": [t.pk for t in Tag.objects.get_for_model(RadioProfile)],
        }
        # Form data for JSONArrayField with choices requires a JSON object, not a string
        # but JSONArrayField renders the data as a string
        cls.expected_data = {
            "name": "New Radio Profile",
            "frequency": choices.RadioProfileFrequencyChoices.FREQUENCY_5G,
            "tx_power_min": 1,
            "tx_power_max": 10,
            "allowed_channel_list": "1,6,11,36,161,165",
            "channel_width": "20,40",
            "regulatory_domain": choices.RadioProfileRegulatoryDomainChoices.US,
            "rx_power_min": -90,
            "tags": [t.pk for t in Tag.objects.get_for_model(RadioProfile)],
        }
        cls.bulk_edit_data = {
            "frequency": choices.RadioProfileFrequencyChoices.FREQUENCY_2_4G,
            "tx_power_min": 2,
            "tx_power_max": 11,
            "allowed_channel_list": "1,2",
            "channel_width": [20, 40, 80, 160],
            "regulatory_domain": choices.RadioProfileRegulatoryDomainChoices.JP,
            "rx_power_min": -89,
        }
        # Form data for JSONArrayField with choices requires a JSON object, not a string
        # but JSONArrayField renders the data as a string
        cls.bulk_edit_expected_data = {
            "frequency": choices.RadioProfileFrequencyChoices.FREQUENCY_2_4G,
            "tx_power_min": 2,
            "tx_power_max": 11,
            "allowed_channel_list": "1,2",
            "channel_width": "20,40,80,160",
            "regulatory_domain": choices.RadioProfileRegulatoryDomainChoices.JP,
            "rx_power_min": -89,
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_create_object_with_permission(self):
        """Override the default test to support the channel_width field."""
        initial_count = self._get_queryset().count()

        # Assign unconstrained permission
        self.add_permissions(f"{self.model._meta.app_label}.add_{self.model._meta.model_name}")

        # Try GET with model-level permission
        self.assertHttpStatus(self.client.get(self._get_url("add")), 200)

        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": utils.post_data(self.form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(initial_count + 1, self._get_queryset().count())
        # order_by() is no supported by django TreeNode,
        # So we directly retrieve the instance by "slug" or "name".
        if isinstance(self._get_queryset().first(), TreeNode):
            filter_by = self.slug_source if getattr(self, "slug_source", None) else "name"
            instance = self._get_queryset().get(**{filter_by: self.form_data.get(filter_by)})
            # Override the self.form_data with self.expected_data in this overridden method
            self.assertInstanceEqual(instance, self.expected_data)
        else:
            if hasattr(self.model, "last_updated"):
                instance = self._get_queryset().order_by("last_updated").last()
                # Override the self.form_data with self.expected_data in this overridden method
                self.assertInstanceEqual(instance, self.expected_data)
            else:
                instance = self._get_queryset().last()
                # Override the self.form_data with self.expected_data in this overridden method
                self.assertInstanceEqual(instance, self.expected_data)

        if hasattr(self.model, "to_objectchange"):
            # Verify ObjectChange creation
            objectchanges = lookup.get_changes_for_model(instance)
            self.assertEqual(len(objectchanges), 1)
            # Assert that Created By table row is updated with the user that created the object
            self.assertEqual(objectchanges[0].action, extras_choices.ObjectChangeActionChoices.ACTION_CREATE)
            # Validate if detail view exists
            validate = URLValidator()
            try:
                detail_url = instance.get_absolute_url()
                validate(detail_url)
                response = self.client.get(detail_url)
                response_body = utils.extract_page_body(response.content.decode(response.charset))
                advanced_tab_href = f"{detail_url}#advanced"
                self.assertIn(advanced_tab_href, response_body)
                self.assertIn("<td>Created By</td>", response_body)
                self.assertIn("<td>nautobotuser</td>", response_body)
            except (AttributeError, ValidationError):
                # Instance does not have a valid detail view, do nothing here.
                pass

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_create_object_with_constrained_permission(self):
        """Override the default test to support the channel_width field."""
        initial_count = self._get_queryset().count()

        # Assign constrained permission
        obj_perm = users_models.ObjectPermission(
            name="Test permission",
            constraints={"pk": str(uuid.uuid4())},  # Match a non-existent pk (i.e., deny all)
            actions=["add"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        # Try GET with object-level permission
        self.assertHttpStatus(self.client.get(self._get_url("add")), 200)

        # Try to create an object (not permitted)
        request = {
            "path": self._get_url("add"),
            "data": utils.post_data(self.form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 200)
        self.assertEqual(initial_count, self._get_queryset().count())  # Check that no object was created

        # Update the ObjectPermission to allow creation
        obj_perm.constraints = {"pk__isnull": False}
        obj_perm.save()

        # Try to create an object (permitted)
        request = {
            "path": self._get_url("add"),
            "data": utils.post_data(self.form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(initial_count + 1, self._get_queryset().count())
        # order_by() is no supported by django TreeNode,
        # So we directly retrieve the instance by "slug".
        if isinstance(self._get_queryset().first(), TreeNode):
            filter_by = self.slug_source if getattr(self, "slug_source", None) else "name"
            instance = self._get_queryset().get(**{filter_by: self.form_data.get(filter_by)})
            # Override the self.form_data with self.expected_data in this overridden method
            self.assertInstanceEqual(instance, self.expected_data)
        else:
            if hasattr(self.model, "last_updated"):
                # Override the self.form_data with self.expected_data in this overridden method
                self.assertInstanceEqual(self._get_queryset().order_by("last_updated").last(), self.expected_data)
            else:
                # Override the self.form_data with self.expected_data in this overridden method
                self.assertInstanceEqual(self._get_queryset().last(), self.expected_data)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_edit_object_with_permission(self):
        """Override the default test to support the channel_width field."""
        instance = self._get_queryset().first()

        # Assign model-level permission
        self.add_permissions(f"{self.model._meta.app_label}.change_{self.model._meta.model_name}")

        # Try GET with model-level permission
        self.assertHttpStatus(self.client.get(self._get_url("edit", instance)), 200)

        # Try POST with model-level permission
        update_data = self.update_data or self.form_data
        request = {
            "path": self._get_url("edit", instance),
            "data": utils.post_data(update_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        # Override update_data with self.expected_data in this overridden method
        self.assertInstanceEqual(self._get_queryset().get(pk=instance.pk), self.expected_data)

        if hasattr(self.model, "to_objectchange"):
            # Verify ObjectChange creation
            objectchanges = lookup.get_changes_for_model(instance)
            self.assertEqual(objectchanges[0].action, extras_choices.ObjectChangeActionChoices.ACTION_UPDATE)
            # Validate if detail view exists
            validate = URLValidator()
            try:
                detail_url = instance.get_absolute_url()
                validate(detail_url)
                response = self.client.get(detail_url)
                response_body = utils.extract_page_body(response.content.decode(response.charset))
                advanced_tab_href = f"{detail_url}#advanced"
                self.assertIn(advanced_tab_href, response_body)
                self.assertIn("<td>Last Updated By</td>", response_body)
                self.assertIn("<td>nautobotuser</td>", response_body)
            except (AttributeError, ValidationError):
                # Instance does not have a valid detail view, do nothing here.
                pass

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_edit_object_with_constrained_permission(self):
        """Override the default test to support the channel_width field."""
        instance1, instance2 = self._get_queryset().all()[:2]

        # Assign constrained permission
        obj_perm = users_models.ObjectPermission(
            name="Test permission",
            constraints={"pk": instance1.pk},
            actions=["change"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        # Try GET with a permitted object
        self.assertHttpStatus(self.client.get(self._get_url("edit", instance1)), 200)

        # Try GET with a non-permitted object
        self.assertHttpStatus(self.client.get(self._get_url("edit", instance2)), 404)

        # Try to edit a permitted object
        update_data = self.update_data or self.form_data
        request = {
            "path": self._get_url("edit", instance1),
            "data": utils.post_data(update_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        # Override update_data with self.expected_data in this overridden method
        self.assertInstanceEqual(self._get_queryset().get(pk=instance1.pk), self.expected_data)

        # Try to edit a non-permitted object
        request = {
            "path": self._get_url("edit", instance2),
            "data": utils.post_data(update_data),
        }
        self.assertHttpStatus(self.client.post(**request), 404)

    def validate_object_data_after_bulk_edit(self, pk_list):
        for instance in self._get_queryset().filter(pk__in=pk_list):
            # Override the self.bulk_edit_data with self.bulk_edit_expected_data in this overridden method
            self.assertInstanceEqual(instance, self.bulk_edit_expected_data)
