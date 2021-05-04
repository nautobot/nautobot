from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from nautobot.dcim.forms import DeviceForm
import nautobot.dcim.models as dcim_models
from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.models import Relationship, RelationshipAssociation, Status
from nautobot.ipam.forms import IPAddressForm, VLANGroupForm
import nautobot.ipam.models as ipam_models


class RelationshipModelFormTestCase(TestCase):
    """
    Test RelationshipModelForm validation and saving.
    """

    @classmethod
    def setUpTestData(cls):
        cls.site = dcim_models.Site.objects.create(name="Site 1", slug="site-1")
        cls.manufacturer = dcim_models.Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        cls.device_type = dcim_models.DeviceType.objects.create(model="Device Type 1", manufacturer=cls.manufacturer)
        cls.device_role = dcim_models.DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        cls.platform = dcim_models.Platform.objects.create(name="Platform 1", slug="platform-1")
        cls.status_active = Status.objects.get(slug="active")
        cls.device_1 = dcim_models.Device.objects.create(
            name="Device 1",
            site=cls.site,
            device_type=cls.device_type,
            device_role=cls.device_role,
            platform=cls.platform,
            status=cls.status_active,
        )
        cls.device_2 = dcim_models.Device.objects.create(
            name="Device 1",
            site=cls.site,
            device_type=cls.device_type,
            device_role=cls.device_role,
            platform=cls.platform,
            status=cls.status_active,
        )

        cls.ipaddress_1 = ipam_models.IPAddress.objects.create(address="10.1.1.1/24", status=cls.status_active)
        cls.ipaddress_2 = ipam_models.IPAddress.objects.create(address="10.2.2.2/24", status=cls.status_active)

        cls.vlangroup_1 = ipam_models.VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1", site=cls.site)
        cls.vlangroup_2 = ipam_models.VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2", site=cls.site)

        cls.relationship_1 = Relationship.objects.create(
            name="BGP Router-ID",
            slug="bgp-router-id",
            source_type=ContentType.objects.get_for_model(dcim_models.Device),
            destination_type=ContentType.objects.get_for_model(ipam_models.IPAddress),
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        cls.relationship_2 = Relationship.objects.create(
            name="Device VLAN Groups",
            slug="device-vlan-groups",
            source_type=ContentType.objects.get_for_model(dcim_models.Device),
            destination_type=ContentType.objects.get_for_model(ipam_models.VLANGroup),
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )

        cls.device_form_base_data = {
            "name": "New Device",
            "device_role": cls.device_role.pk,
            "tenant": None,
            "manufacturer": cls.manufacturer.pk,
            "device_type": cls.device_type.pk,
            "site": cls.site.pk,
            "rack": None,
            "face": None,
            "position": None,
            "platform": cls.platform.pk,
            "status": cls.status_active.pk,
        }
        cls.ipaddress_form_base_data = {
            "address": "10.3.3.3/24",
            "status": cls.status_active.pk,
        }
        cls.vlangroup_form_base_data = {
            "site": cls.site.pk,
            "name": "New VLAN Group",
            "slug": "new-vlan-group",
        }

    def test_create_relationship_associations_valid_1(self):
        """
        A new record can create ONE_TO_ONE and ONE_TO_MANY associations where it is the "source" object.
        """
        form = DeviceForm(
            data=dict(
                **self.device_form_base_data,
                **{
                    f"cr_{self.relationship_1.slug}__destination": self.ipaddress_1.pk,
                    f"cr_{self.relationship_2.slug}__destination": [self.vlangroup_1.pk, self.vlangroup_2.pk],
                },
            )
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

        new_device = dcim_models.Device.objects.get(name=self.device_form_base_data["name"])
        # Verify that RelationshipAssociations were created
        RelationshipAssociation.objects.get(
            relationship=self.relationship_1, source_id=new_device.pk, destination_id=self.ipaddress_1.pk
        )
        RelationshipAssociation.objects.get(
            relationship=self.relationship_2, source_id=new_device.pk, destination_id=self.vlangroup_1.pk
        )
        RelationshipAssociation.objects.get(
            relationship=self.relationship_2, source_id=new_device.pk, destination_id=self.vlangroup_2.pk
        )

    def test_create_relationship_associations_valid_2(self):
        """
        A new record can create ONE_TO_ONE associations where it is the "destination" object.
        """
        form = IPAddressForm(
            data=dict(
                **self.ipaddress_form_base_data,
                **{
                    f"cr_{self.relationship_1.slug}__source": self.device_1.pk,
                },
            )
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())
        new_ip = ipam_models.IPAddress.objects.get(address=self.ipaddress_form_base_data["address"])
        RelationshipAssociation.objects.get(
            relationship=self.relationship_1, source_id=self.device_1.pk, destination_id=new_ip.pk
        )

    def test_create_relationship_associations_valid_3(self):
        """
        A new record can create ONE_TO_MANY associations where it is the "destination" object.
        """
        form = VLANGroupForm(
            data=dict(
                **self.vlangroup_form_base_data,
                **{
                    f"cr_{self.relationship_2.slug}__source": self.device_1.pk,
                },
            )
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())
        new_vlangroup = ipam_models.VLANGroup.objects.get(name=self.vlangroup_form_base_data["name"])
        RelationshipAssociation.objects.get(
            relationship=self.relationship_2, source_id=self.device_1.pk, destination_id=new_vlangroup.pk
        )

    def test_create_relationship_associations_invalid_1(self):
        """
        A new record CANNOT create ONE_TO_ONE relations where its "destination" is already associated.
        """
        # Existing ONE_TO_ONE relation
        RelationshipAssociation.objects.create(
            relationship=self.relationship_1,
            source_type=self.relationship_1.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_1.destination_type,
            destination_id=self.ipaddress_1.pk,
        )

        # Can't associate New Device with IP Address 1 (already associated to Device 1)
        form = DeviceForm(
            data=dict(
                **self.device_form_base_data, **{f"cr_{self.relationship_1.slug}__destination": self.ipaddress_1.pk}
            )
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            "10.1.1.1/24 is already involved in a BGP Router-ID relationship",
            form.errors[f"cr_{self.relationship_1.slug}__destination"][0],
        )

        # Can't associate new IP address with Device 1 (already associated with IP Address 1)
        form = IPAddressForm(
            data=dict(**self.ipaddress_form_base_data, **{f"cr_{self.relationship_1.slug}__source": self.device_1.pk})
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            "Device 1 is already involved in a BGP Router-ID relationship",
            form.errors[f"cr_{self.relationship_1.slug}__source"][0],
        )

    def test_create_relationship_associations_invalid_2(self):
        """
        A new record CANNOT create ONE_TO_MANY relations where any of its "destinations" are already associated.
        """
        # Existing ONE_TO_MANY relation
        RelationshipAssociation.objects.create(
            relationship=self.relationship_2,
            source_type=self.relationship_2.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_2.destination_type,
            destination_id=self.vlangroup_1.pk,
        )

        # Can't associate New Device with VLAN Group 1 (already associated to Device 1)
        form = DeviceForm(
            data=dict(
                **self.device_form_base_data,
                **{f"cr_{self.relationship_2.slug}__destination": [self.vlangroup_1.pk, self.vlangroup_2.pk]},
            )
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            "VLAN Group 1 is already involved in a Device VLAN Groups relationship",
            form.errors[f"cr_{self.relationship_2.slug}__destination"][0],
        )

    def test_update_relationship_associations_valid_1(self):
        """
        An existing record with an existing ONE_TO_ONE or ONE_TO_MANY association can change its destination(s).
        """
        # Existing ONE_TO_ONE relation
        RelationshipAssociation.objects.create(
            relationship=self.relationship_1,
            source_type=self.relationship_1.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_1.destination_type,
            destination_id=self.ipaddress_1.pk,
        )
        # Existing ONE_TO_MANY relation
        RelationshipAssociation.objects.create(
            relationship=self.relationship_2,
            source_type=self.relationship_2.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_2.destination_type,
            destination_id=self.vlangroup_1.pk,
        )

        form = DeviceForm(
            instance=self.device_1,
            data={
                "site": self.site,
                "device_role": self.device_role,
                "device_type": self.device_type,
                "status": self.status_active,
                f"cr_{self.relationship_1.slug}__destination": self.ipaddress_2.pk,
                f"cr_{self.relationship_2.slug}__destination": [self.vlangroup_2.pk],
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.save())

        # Existing ONE_TO_ONE relation should have been deleted and replaced
        with self.assertRaises(RelationshipAssociation.DoesNotExist):
            RelationshipAssociation.objects.get(relationship=self.relationship_1, destination_id=self.ipaddress_1.pk)
        RelationshipAssociation.objects.get(
            relationship=self.relationship_1, source_id=self.device_1.pk, destination_id=self.ipaddress_2.pk
        )

        # Existing ONE_TO_MANY relation should have been deleted and replaced
        with self.assertRaises(RelationshipAssociation.DoesNotExist):
            RelationshipAssociation.objects.get(relationship=self.relationship_2, destination_id=self.vlangroup_1.pk)
        RelationshipAssociation.objects.get(
            relationship=self.relationship_2, source_id=self.device_1.pk, destination_id=self.vlangroup_2.pk
        )

    def test_update_relationship_associations_valid_2(self):
        """
        An existing record with an existing ONE_TO_ONE association can change its source.
        """
        # Existing ONE_TO_ONE relation
        RelationshipAssociation.objects.create(
            relationship=self.relationship_1,
            source_type=self.relationship_1.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_1.destination_type,
            destination_id=self.ipaddress_1.pk,
        )

        form = IPAddressForm(
            instance=self.ipaddress_1,
            data={
                "address": self.ipaddress_1.address,
                "status": self.status_active,
                f"cr_{self.relationship_1.slug}__source": self.device_2.pk,
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.save())

        # Existing ONE_TO_ONE relation should have been deleted and replaced
        with self.assertRaises(RelationshipAssociation.DoesNotExist):
            RelationshipAssociation.objects.get(relationship=self.relationship_1, source_id=self.device_1.pk)
        RelationshipAssociation.objects.get(
            relationship=self.relationship_1, source_id=self.device_2.pk, destination_id=self.ipaddress_1.pk
        )

    def test_update_relationship_associations_valid_3(self):
        """
        An existing record with an existing ONE_TO_MANY association can change its source.
        """
        # Existing ONE_TO_MANY relation
        RelationshipAssociation.objects.create(
            relationship=self.relationship_2,
            source_type=self.relationship_2.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_2.destination_type,
            destination_id=self.vlangroup_1.pk,
        )

        form = VLANGroupForm(
            instance=self.vlangroup_1,
            data={
                "name": self.vlangroup_1.name,
                "slug": self.vlangroup_1.slug,
                "site": self.site,
                f"cr_{self.relationship_2.slug}__source": self.device_2.pk,
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.save())

        # Existing ONE_TO_MANY relation should have been deleted and replaced
        with self.assertRaises(RelationshipAssociation.DoesNotExist):
            RelationshipAssociation.objects.get(relationship=self.relationship_2, source_id=self.device_1.pk)
        RelationshipAssociation.objects.get(
            relationship=self.relationship_2, source_id=self.device_2.pk, destination_id=self.vlangroup_1.pk
        )
