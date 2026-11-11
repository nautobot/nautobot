from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from nautobot.cloud import models
from nautobot.core.testing import TestCase
from nautobot.core.testing.models import ModelTestCases
from nautobot.dcim.models import Location, LocationType, Manufacturer
from nautobot.extras.models import Status


class CloudTestDataMixin:
    """Create two providers, each with resource types and accounts, for deterministic validation tests."""

    @classmethod
    def create_cloud_test_data(cls):
        cls.provider_a = Manufacturer.objects.create(name="Cloud Provider A")
        cls.provider_b = Manufacturer.objects.create(name="Cloud Provider B")
        cls.account_status = Status.objects.get_for_model(models.CloudAccount).first()
        cls.network_status = Status.objects.get_for_model(models.CloudNetwork).first()
        cls.service_status = Status.objects.get_for_model(models.CloudService).first()

        def resource_type(name, provider, model):
            rt = models.CloudResourceType.objects.create(name=name, provider=provider)
            rt.content_types.set([ContentType.objects.get_for_model(model)])
            return rt

        cls.group_type_a = resource_type("Provider A Group", cls.provider_a, models.CloudAccountGroup)
        cls.rg_type_a = resource_type("Provider A Resource Group", cls.provider_a, models.CloudResourceGroup)
        cls.network_type_a = resource_type("Provider A Network", cls.provider_a, models.CloudNetwork)
        cls.network_type_b = resource_type("Provider B Network", cls.provider_b, models.CloudNetwork)
        cls.service_type_a = resource_type("Provider A Service", cls.provider_a, models.CloudService)
        cls.service_type_b = resource_type("Provider B Service", cls.provider_b, models.CloudService)

        cls.account_a1 = models.CloudAccount.objects.create(
            name="Account A1", account_number="1", provider=cls.provider_a, status=cls.account_status
        )
        cls.account_a2 = models.CloudAccount.objects.create(
            name="Account A2", account_number="2", provider=cls.provider_a, status=cls.account_status
        )
        cls.rg_a1 = models.CloudResourceGroup.objects.create(
            name="Resource Group 1", cloud_account=cls.account_a1, cloud_resource_type=cls.rg_type_a
        )

    def make_network(self, **kwargs):
        defaults = {
            "name": "Network",
            "cloud_account": self.account_a1,
            "cloud_resource_type": self.network_type_a,
            "status": self.network_status,
        }
        defaults.update(kwargs)
        return models.CloudNetwork(**defaults)

    def make_service(self, **kwargs):
        defaults = {
            "name": "Service",
            "cloud_account": self.account_a1,
            "cloud_resource_type": self.service_type_a,
            "status": self.service_status,
        }
        defaults.update(kwargs)
        return models.CloudService(**defaults)


class CloudAccountModelTestCase(ModelTestCases.BaseModelTestCase):
    model = models.CloudAccount


class CloudAccountUniquenessTestCase(CloudTestDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_cloud_test_data()

    def test_name_unique_per_provider(self):
        models.CloudAccount(
            name="Account A1", account_number="3", provider=self.provider_b, status=self.account_status
        ).validated_save()
        with self.assertRaises(ValidationError):
            models.CloudAccount(
                name="Account A1", account_number="4", provider=self.provider_a, status=self.account_status
            ).validated_save()


class CloudAccountGroupModelTestCase(ModelTestCases.BaseModelTestCase):
    model = models.CloudAccountGroup


class CloudAccountGroupUniquenessTestCase(CloudTestDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_cloud_test_data()
        cls.root = models.CloudAccountGroup.objects.create(name="Root", cloud_resource_type=cls.group_type_a)

    def test_name_unique_within_parent(self):
        models.CloudAccountGroup(
            name="Workloads", parent=self.root, cloud_resource_type=self.group_type_a
        ).validated_save()
        models.CloudAccountGroup(name="Workloads", cloud_resource_type=self.group_type_a).validated_save()
        with self.assertRaises(ValidationError):
            models.CloudAccountGroup(
                name="Workloads", parent=self.root, cloud_resource_type=self.group_type_a
            ).validated_save()

    def test_top_level_name_unique(self):
        with self.assertRaises(ValidationError) as cm:
            models.CloudAccountGroup(name="Root", cloud_resource_type=self.group_type_a).validated_save()
        self.assertIn("name", cm.exception.message_dict)


class CloudResourceGroupModelTestCase(ModelTestCases.BaseModelTestCase):
    model = models.CloudResourceGroup


class CloudResourceGroupValidationTestCase(CloudTestDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_cloud_test_data()
        location_type = LocationType.objects.create(name="Cloud Resource Group Test Type")
        cls.location = Location.objects.create(
            name="Not For Cloud", location_type=location_type, status=Status.objects.get_for_model(Location).first()
        )

    def test_name_unique_within_account(self):
        models.CloudResourceGroup(
            name="Resource Group 1", cloud_account=self.account_a2, cloud_resource_type=self.rg_type_a
        ).validated_save()
        with self.assertRaises(ValidationError):
            models.CloudResourceGroup(
                name="Resource Group 1", cloud_account=self.account_a1, cloud_resource_type=self.rg_type_a
            ).validated_save()

    def test_location_must_permit_content_type(self):
        rg = models.CloudResourceGroup(
            name="Located", cloud_account=self.account_a1, cloud_resource_type=self.rg_type_a, location=self.location
        )
        with self.assertRaises(ValidationError) as cm:
            rg.validated_save()
        self.assertIn("location", cm.exception.message_dict)

        self.location.location_type.content_types.add(ContentType.objects.get_for_model(models.CloudResourceGroup))
        rg.validated_save()


class CloudResourceTypeModelTestCase(ModelTestCases.BaseModelTestCase):
    model = models.CloudResourceType


class CloudNetworkModelTestCase(ModelTestCases.BaseModelTestCase):
    model = models.CloudNetwork

    def test_parent_may_not_have_parent(self):
        illegal_parent = models.CloudNetwork.objects.filter(parent__isnull=False).first()
        with self.assertRaises(ValidationError):
            models.CloudNetwork(
                name="Grandchild",
                cloud_account=illegal_parent.cloud_account,
                cloud_resource_type=illegal_parent.cloud_resource_type,
                status=illegal_parent.status,
                parent=illegal_parent,
            ).clean()

    def test_parent_may_not_be_self(self):
        existing = models.CloudNetwork.objects.last()
        cloud_network = models.CloudNetwork(
            name="Loop",
            cloud_account=existing.cloud_account,
            cloud_resource_type=existing.cloud_resource_type,
            status=existing.status,
        )
        cloud_network.validated_save()
        with self.assertRaises(ValidationError):
            cloud_network.parent = cloud_network
            cloud_network.clean()

    # TODO: test schema validation of extra_config


class CloudNetworkValidationTestCase(CloudTestDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_cloud_test_data()

    def test_same_name_allowed_in_different_accounts(self):
        self.make_network(name="vnet-hub").validated_save()
        self.make_network(name="vnet-hub", cloud_account=self.account_a2).validated_save()

    def test_same_name_allowed_in_different_resource_groups(self):
        self.make_network(name="vnet-hub").validated_save()
        self.make_network(name="vnet-hub", cloud_resource_group=self.rg_a1).validated_save()

    def test_duplicate_name_rejected_in_same_scope(self):
        self.make_network(name="vnet-hub", cloud_resource_group=self.rg_a1).validated_save()
        with self.assertRaises(ValidationError):
            self.make_network(name="vnet-hub", cloud_resource_group=self.rg_a1).validated_save()

    def test_duplicate_name_rejected_when_scope_fields_are_empty(self):
        self.make_network(name="vnet-hub").validated_save()
        with self.assertRaises(ValidationError) as cm:
            self.make_network(name="vnet-hub").validated_save()
        self.assertIn("name", cm.exception.message_dict)

    def test_provider_resource_id_unique_when_set(self):
        self.make_network(name="vnet-1", provider_resource_id="/subscriptions/1/vnet-1").validated_save()
        self.make_network(name="vnet-2").validated_save()
        self.make_network(name="vnet-3").validated_save()
        with self.assertRaises(ValidationError) as cm:
            self.make_network(name="vnet-4", provider_resource_id="/subscriptions/1/vnet-1").validated_save()
        self.assertIn("provider_resource_id", cm.exception.message_dict)

    def test_resource_group_must_belong_to_same_account(self):
        with self.assertRaises(ValidationError) as cm:
            self.make_network(cloud_account=self.account_a2, cloud_resource_group=self.rg_a1).validated_save()
        self.assertIn("cloud_resource_group", cm.exception.message_dict)

    def test_resource_type_provider_must_match_account_provider(self):
        with self.assertRaises(ValidationError) as cm:
            self.make_network(cloud_resource_type=self.network_type_b).validated_save()
        self.assertIn("cloud_resource_type", cm.exception.message_dict)

    def test_parent_must_belong_to_same_account(self):
        parent = self.make_network(name="vnet-parent")
        parent.validated_save()
        with self.assertRaises(ValidationError) as cm:
            self.make_network(name="subnet", cloud_account=self.account_a2, parent=parent).validated_save()
        self.assertIn("parent", cm.exception.message_dict)


class CloudNetworkPrefixAssignmentModelTestCase(ModelTestCases.BaseModelTestCase):
    model = models.CloudNetworkPrefixAssignment


class CloudServiceModelTestCase(ModelTestCases.BaseModelTestCase):
    model = models.CloudService


class CloudServiceValidationTestCase(CloudTestDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_cloud_test_data()

    def test_duplicate_name_rejected_without_account(self):
        self.make_service(name="dns-zone", cloud_account=None).validated_save()
        with self.assertRaises(ValidationError):
            self.make_service(name="dns-zone", cloud_account=None).validated_save()

    def test_same_name_allowed_in_different_accounts(self):
        self.make_service(name="database").validated_save()
        self.make_service(name="database", cloud_account=self.account_a2).validated_save()

    def test_resource_group_must_belong_to_same_account(self):
        with self.assertRaises(ValidationError) as cm:
            self.make_service(cloud_account=self.account_a2, cloud_resource_group=self.rg_a1).validated_save()
        self.assertIn("cloud_resource_group", cm.exception.message_dict)

    def test_resource_type_provider_must_match_account_provider(self):
        with self.assertRaises(ValidationError) as cm:
            self.make_service(cloud_resource_type=self.service_type_b).validated_save()
        self.assertIn("cloud_resource_type", cm.exception.message_dict)

    def test_resource_type_of_any_provider_allowed_without_account(self):
        self.make_service(cloud_account=None, cloud_resource_type=self.service_type_b).validated_save()


class CloudServiceIPAddressAssignmentModelTestCase(ModelTestCases.BaseModelTestCase):
    model = models.CloudServiceIPAddressAssignment
