import json
import warnings

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.test import TestCase, override_settings

from nautobot.dcim.forms import DeviceForm, LocationBulkEditForm, LocationForm
import nautobot.dcim.models as dcim_models
from nautobot.dcim.models import Device, Location, LocationType
from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.forms import (
    ConfigContextForm,
    ConfigContextFilterForm,
    CustomFieldModelBulkEditFormMixin,
    CustomFieldModelFilterFormMixin,
    CustomFieldModelFormMixin,
    JobButtonForm,
    JobEditForm,
    JobHookForm,
    RelationshipModelFormMixin,
    StatusModelBulkEditFormMixin,
    StatusModelFilterFormMixin,
    TagsBulkEditFormMixin,
    WebhookForm,
)
from nautobot.extras.models import (
    Job,
    JobButton,
    JobHook,
    Note,
    Relationship,
    RelationshipAssociation,
    Role,
    Status,
    Webhook,
)
from nautobot.ipam.choices import IPAddressTypeChoices
from nautobot.ipam.forms import IPAddressForm, IPAddressBulkEditForm, VLANGroupForm
import nautobot.ipam.models as ipam_models


# Use the proper swappable User model
User = get_user_model()


class JobHookFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        job_hook = JobHook.objects.create(
            name="JobHook1",
            job=Job.objects.get(job_class_name="TestJobHookReceiverLog"),
            type_create=True,
            type_update=True,
            type_delete=False,
        )
        devicetype_ct = ContentType.objects.get_for_model(dcim_models.DeviceType)
        location_ct = ContentType.objects.get_for_model(dcim_models.Location)
        job_hook.content_types.set([devicetype_ct])

        cls.job_hooks_data = (
            {
                "name": "JobHook2",
                "content_types": [devicetype_ct.pk],
                "job": Job.objects.get(job_class_name="TestJobHookReceiverChange"),
                "type_create": True,
                "type_update": True,
                "type_delete": False,
            },
            {
                "name": "JobHook3",
                "content_types": [devicetype_ct.pk],
                "job": Job.objects.get(job_class_name="TestJobHookReceiverLog"),
                "type_create": False,
                "type_update": False,
                "type_delete": True,
            },
            {
                "name": "JobHook4",
                "content_types": [location_ct.pk],
                "job": Job.objects.get(job_class_name="TestJobHookReceiverLog"),
                "type_create": True,
                "type_update": True,
                "type_delete": True,
            },
            {
                "name": "JobHook5",
                "content_types": [devicetype_ct.pk],
                "job": Job.objects.get(job_class_name="TestJobHookReceiverLog"),
                "type_create": True,
                "type_update": True,
                "type_delete": True,
            },
        )

    def test_create_job_hooks_with_same_content_type_same_action_diff_job(self):
        """
        Create a new job hook with the same content_types, same action and different job from a job hook that exists

        Example:
            Job hook 1: dcim | device type, create, update, Job(job_class_name="TestJobHookReceiverLog")
            Job hook 2: dcim | device type, create, update, Job(job_class_name="TestJobHookReceiverChange")
        """
        form = JobHookForm(data=self.job_hooks_data[0])

        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(JobHook.objects.filter(name=self.job_hooks_data[0]["name"]).count(), 1)

    def test_create_job_hooks_with_same_content_type_same_job_diff_action(self):
        """
        Create a new job hook with the same content_types, same job and different actions from a job hook that exists

        Example:
            Job hook 1: dcim | device type, create, update, Job(job_class_name="TestJobHookReceiverLog")
            Job hook 2: dcim | device type, delete, Job(job_class_name="TestJobHookReceiverLog")
        """
        form = JobHookForm(data=self.job_hooks_data[1])

        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(JobHook.objects.filter(name=self.job_hooks_data[1]["name"]).count(), 1)

    def test_create_job_hooks_with_same_job_same_action_diff_content_type(self):
        """
        Create a new job hook with the same job, same actions and different content types from a job hook that exists

        Example:
            Job hook 1: dcim | device type, create, update, Job(job_class_name="TestJobHookReceiverLog")
            Job hook 2: dcim | location, create, update, Job(job_class_name="TestJobHookReceiverLog")
        """
        form = JobHookForm(data=self.job_hooks_data[2])

        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(JobHook.objects.filter(name=self.job_hooks_data[2]["name"]).count(), 1)

    def test_create_job_hooks_with_same_job_common_action_same_content_type(self):
        """
        Create a new job hook with the same job, common actions and same content types as a job hook that exists

        Example:
            Job hook 1: dcim | device type, create, update, Job(job_class_name="TestJobHookReceiverLog")
            Job hook 2: dcim | device type, create, update, delete, Job(job_class_name="TestJobHookReceiverLog")
        """
        form = JobHookForm(data=self.job_hooks_data[3])

        self.assertFalse(form.is_valid())
        error_msg = json.loads(form.errors.as_json())

        self.assertEqual(JobHook.objects.filter(name=self.job_hooks_data[3]["name"]).count(), 0)
        self.assertIn("type_create", error_msg)
        self.assertEqual(
            error_msg["type_create"][0]["message"],
            "A job hook already exists for create on dcim | device type to job TestJobHookReceiverLog",
        )
        self.assertEqual(
            error_msg["type_update"][0]["message"],
            "A job hook already exists for update on dcim | device type to job TestJobHookReceiverLog",
        )


class JobButtonFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        job_button = JobButton.objects.create(
            name="JobButton1",
            text="JobButton1",
            job=Job.objects.get(job_class_name="TestJobButtonReceiverComplex"),
        )
        device_ct = ContentType.objects.get_for_model(dcim_models.Device)
        location_ct = ContentType.objects.get_for_model(dcim_models.Location)
        job_button.content_types.set([device_ct])

        cls.job_buttons_data = (
            {
                "name": "JobButton2",
                "text": "JobButton2",
                "content_types": [device_ct.pk],
                "job": Job.objects.get(job_class_name="TestJobButtonReceiverSimple"),
                "weight": 100,
                "button_class": "primary",
            },
            {
                "name": "JobButton3",
                "text": "JobButton3",
                "content_types": [location_ct.pk],
                "job": Job.objects.get(job_class_name="TestJobButtonReceiverComplex"),
                "weight": 100,
                "button_class": "primary",
            },
        )

    def test_create_job_button_with_same_content_type_diff_job(self):
        """
        Create a new job button with the same content_types and different job from a job button that exists

        Example:
            Job button 1: dcim | device, Job(job_class_name="TestJobButtonReceiverComplex")
            Job button 2: dcim | device, Job(job_class_name="TestJobButtonReceiverSimple")
        """
        form = JobButtonForm(data=self.job_buttons_data[0])

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.assertEqual(JobButton.objects.filter(name=self.job_buttons_data[0]["name"]).count(), 1)

    def test_create_job_button_with_same_job_diff_content_type(self):
        """
        Create a new job button with the same job and different content types from a job button that exists

        Example:
            Job button 1: dcim | device, Job(job_class_name="TestJobButtonReceiverComplex")
            Job button 2: dcim | location, Job(job_class_name="TestJobButtonReceiverComplex")
        """
        form = JobButtonForm(data=self.job_buttons_data[1])

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.assertEqual(JobButton.objects.filter(name=self.job_buttons_data[1]["name"]).count(), 1)


class NoteModelFormTestCase(TestCase):
    """
    TestNoteModelForm validation and saving.
    """

    @classmethod
    def setUpTestData(cls):
        status = Status.objects.get_for_model(Location).first()
        cls.user = User.objects.create(username="formuser1")
        cls.location_type = LocationType.objects.get(name="Campus")

        cls.location_form_base_data = {
            "name": "Location 1",
            "location_type": cls.location_type.pk,
            "status": status.pk,
        }

    def test_note_object_edit_form(self):
        form = LocationForm(data={**self.location_form_base_data, "object_note": "This is a test."})
        self.assertTrue(form.is_valid())
        obj = form.save()
        form.save_note(
            instance=obj,
            user=self.user,
        )
        note = Note.objects.first()
        self.assertEqual(1, Note.objects.count())
        self.assertEqual("This is a test.", note.note)
        self.assertEqual(obj, note.assigned_object)
        self.assertEqual(self.user, note.user)


class NoteModelBulkEditFormMixinTestCase(TestCase):
    """
    TestNoteModelForm validation and saving.
    """

    @classmethod
    def setUpTestData(cls):
        cls.locations = dcim_models.Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]
        cls.user = User.objects.create(username="formuser1")

    def test_note_bulk_edit(self):
        form = LocationBulkEditForm(
            model=dcim_models.Location,
            data={"pks": [location.pk for location in self.locations], "object_note": "Test"},
        )
        form.is_valid()
        form.save_note(
            instance=self.locations[0],
            user=self.user,
        )
        form.save_note(
            instance=self.locations[1],
            user=self.user,
        )
        notes = Note.objects.all()
        self.assertEqual(2, Note.objects.count())
        self.assertEqual("Test", notes[0].note)
        self.assertEqual("Test", notes[1].note)


class RelationshipModelFormTestCase(TestCase):
    """
    Test RelationshipModelForm validation and saving.
    """

    @classmethod
    def setUpTestData(cls):
        cls.location = dcim_models.Location.objects.filter(
            location_type=LocationType.objects.get(name="Campus")
        ).first()
        cls.manufacturer = dcim_models.Manufacturer.objects.first()
        cls.device_type = dcim_models.DeviceType.objects.create(model="Device Type 1", manufacturer=cls.manufacturer)
        cls.device_role = Role.objects.get_for_model(Device).first()
        cls.platform = dcim_models.Platform.objects.create(name="Platform 1")
        cls.device_status = Status.objects.get_for_model(Device).first()
        cls.ipaddress_status = Status.objects.get_for_model(ipam_models.IPAddress).first()
        cls.prefix_status = Status.objects.get_for_model(ipam_models.Prefix).first()
        cls.vlangroup_status = Status.objects.get_for_model(ipam_models.VLANGroup).first()
        cls.device_1 = dcim_models.Device.objects.create(
            name="Device 1",
            location=cls.location,
            device_type=cls.device_type,
            role=cls.device_role,
            platform=cls.platform,
            status=cls.device_status,
        )
        cls.device_2 = dcim_models.Device.objects.create(
            name="Device 2",
            location=cls.location,
            device_type=cls.device_type,
            role=cls.device_role,
            platform=cls.platform,
            status=cls.device_status,
        )
        cls.device_3 = dcim_models.Device.objects.create(
            name="Device 3",
            location=cls.location,
            device_type=cls.device_type,
            role=cls.device_role,
            platform=cls.platform,
            status=cls.device_status,
        )

        cls.namespace = ipam_models.Namespace.objects.create(name="test_forms RelationshipModelFormTestCase")
        ipam_models.Prefix.objects.create(prefix="10.0.0.0/8", namespace=cls.namespace, status=cls.prefix_status)
        cls.ipaddress_1 = ipam_models.IPAddress.objects.create(
            address="10.1.1.1/24", namespace=cls.namespace, status=cls.ipaddress_status
        )
        cls.ipaddress_2 = ipam_models.IPAddress.objects.create(
            address="10.2.2.2/24", namespace=cls.namespace, status=cls.ipaddress_status
        )

        cls.vlangroup_1 = ipam_models.VLANGroup.objects.create(name="VLAN Group 1", location=cls.location)
        cls.vlangroup_2 = ipam_models.VLANGroup.objects.create(name="VLAN Group 2", location=cls.location)

        cls.relationship_1 = Relationship(
            label="BGP Router-ID",
            key="bgp_router_id",
            source_type=ContentType.objects.get_for_model(dcim_models.Device),
            destination_type=ContentType.objects.get_for_model(ipam_models.IPAddress),
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        cls.relationship_1.validated_save()
        cls.relationship_2 = Relationship(
            label="Device VLAN Groups",
            key="device_vlan_groups",
            source_type=ContentType.objects.get_for_model(dcim_models.Device),
            destination_type=ContentType.objects.get_for_model(ipam_models.VLANGroup),
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )
        cls.relationship_2.validated_save()
        cls.relationship_3 = Relationship(
            label="HA Device Peer",
            key="ha_device_peer",
            source_type=ContentType.objects.get_for_model(dcim_models.Device),
            destination_type=ContentType.objects.get_for_model(dcim_models.Device),
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
        )
        cls.relationship_3.validated_save()

        cls.device_form_base_data = {
            "name": "New Device",
            "role": cls.device_role.pk,
            "tenant": None,
            "manufacturer": cls.manufacturer.pk,
            "device_type": cls.device_type.pk,
            "location": cls.location.pk,
            "rack": None,
            "face": None,
            "position": None,
            "platform": cls.platform.pk,
            "status": cls.device_status.pk,
        }
        cls.ipaddress_form_base_data = {
            "address": "10.3.3.3/24",
            "namespace": cls.namespace.pk,
            "status": cls.ipaddress_status.pk,
            "type": IPAddressTypeChoices.TYPE_HOST,
        }
        cls.vlangroup_form_base_data = {
            "location": cls.location.pk,
            "name": "New VLAN Group",
        }

    def test_create_relationship_associations_valid_1(self):
        """
        A new record can create ONE_TO_ONE and ONE_TO_MANY associations where it is the "source" object.

        It can also create ONE_TO_ONE_SYMMETRIC associations where it is a "peer" object.
        """
        form = DeviceForm(
            data={
                **self.device_form_base_data,
                f"cr_{self.relationship_1.key}__destination": self.ipaddress_1.pk,
                f"cr_{self.relationship_2.key}__destination": [self.vlangroup_1.pk, self.vlangroup_2.pk],
                f"cr_{self.relationship_3.key}__peer": self.device_1.pk,
            }
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
        # relationship_3 is symmetric, we don't care which side is "source" or "destination" as long as it exists
        RelationshipAssociation.objects.get(
            Q(source_id=new_device.pk, destination_id=self.device_1.pk)
            | Q(source_id=self.device_1.pk, destination_id=new_device.pk),
            relationship=self.relationship_3,
        )

    def test_create_relationship_associations_valid_2(self):
        """
        A new record can create ONE_TO_ONE associations where it is the "destination" object.
        """
        form = IPAddressForm(
            data={
                **self.ipaddress_form_base_data,
                f"cr_{self.relationship_1.key}__source": self.device_1.pk,
            }
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
            data={
                **self.vlangroup_form_base_data,
                f"cr_{self.relationship_2.key}__source": self.device_1.pk,
            }
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
        RelationshipAssociation(
            relationship=self.relationship_1,
            source_type=self.relationship_1.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_1.destination_type,
            destination_id=self.ipaddress_1.pk,
        ).validated_save()

        # Can't associate New Device with IP Address 1 (already associated to Device 1)
        form = DeviceForm(
            data={**self.device_form_base_data, f"cr_{self.relationship_1.key}__destination": self.ipaddress_1.pk}
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            "10.1.1.1/24 is already involved in a BGP Router-ID relationship",
            form.errors[f"cr_{self.relationship_1.key}__destination"][0],
        )

        # Can't associate new IP address with Device 1 (already associated with IP Address 1)
        form = IPAddressForm(
            data={**self.ipaddress_form_base_data, f"cr_{self.relationship_1.key}__source": self.device_1.pk}
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            "Device 1 is already involved in a BGP Router-ID relationship",
            form.errors[f"cr_{self.relationship_1.key}__source"][0],
        )

    def test_create_relationship_associations_invalid_2(self):
        """
        A new record CANNOT create ONE_TO_MANY relations where any of its "destinations" are already associated.
        """
        # Existing ONE_TO_MANY relation
        RelationshipAssociation(
            relationship=self.relationship_2,
            source_type=self.relationship_2.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_2.destination_type,
            destination_id=self.vlangroup_1.pk,
        ).validated_save()

        # Can't associate New Device with VLAN Group 1 (already associated to Device 1)
        form = DeviceForm(
            data={
                **self.device_form_base_data,
                f"cr_{self.relationship_2.key}__destination": [self.vlangroup_1.pk, self.vlangroup_2.pk],
            }
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            "VLAN Group 1 is already involved in a Device VLAN Groups relationship",
            form.errors[f"cr_{self.relationship_2.key}__destination"][0],
        )

    def test_create_relationship_associations_invalid_3(self):
        """
        A new record CANNOT create ONE_TO_ONE_SYMMETRIC relations where its peer is already associated.
        """
        # Existing ONE_TO_ONE_SYMMETRIC relation
        RelationshipAssociation(
            relationship=self.relationship_3,
            source_type=self.relationship_3.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_3.destination_type,
            destination_id=self.device_2.pk,
        ).validated_save()

        # Peer is already a source for this relationship
        form = DeviceForm(data={**self.device_form_base_data, f"cr_{self.relationship_3.key}__peer": self.device_1.pk})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            "Device 1 is already involved in a HA Device Peer relationship",
            form.errors[f"cr_{self.relationship_3.key}__peer"][0],
        )

        # Peer is already a destination for this relationship
        form = DeviceForm(data={**self.device_form_base_data, f"cr_{self.relationship_3.key}__peer": self.device_2.pk})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            "Device 2 is already involved in a HA Device Peer relationship",
            form.errors[f"cr_{self.relationship_3.key}__peer"][0],
        )

    def test_update_relationship_associations_valid_1(self):
        """
        An existing record with an existing ONE_TO_ONE or ONE_TO_MANY association can change its destination(s).
        """
        # Existing ONE_TO_ONE relation
        RelationshipAssociation(
            relationship=self.relationship_1,
            source_type=self.relationship_1.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_1.destination_type,
            destination_id=self.ipaddress_1.pk,
        ).validated_save()
        # Existing ONE_TO_MANY relation
        RelationshipAssociation(
            relationship=self.relationship_2,
            source_type=self.relationship_2.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_2.destination_type,
            destination_id=self.vlangroup_1.pk,
        ).validated_save()
        # Existing ONE_TO_ONE_SYMMETRIC relation
        RelationshipAssociation(
            relationship=self.relationship_3,
            source_type=self.relationship_3.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_3.destination_type,
            destination_id=self.device_3.pk,
        ).validated_save()

        form = DeviceForm(
            instance=self.device_1,
            data={
                "location": self.location,
                "role": self.device_role,
                "device_type": self.device_type,
                "status": self.device_status,
                f"cr_{self.relationship_1.key}__destination": self.ipaddress_2.pk,
                f"cr_{self.relationship_2.key}__destination": [self.vlangroup_2.pk],
                f"cr_{self.relationship_3.key}__peer": self.device_2.pk,
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

        # Existing ONE_TO_ONE_SYMMETRIC relation should have been deleted and replaced
        with self.assertRaises(RelationshipAssociation.DoesNotExist):
            RelationshipAssociation.objects.get(relationship=self.relationship_3, destination_id=self.device_3.pk)
        RelationshipAssociation.objects.get(
            Q(source_id=self.device_1.pk, destination_id=self.device_2.pk)
            | Q(source_id=self.device_2.pk, destination_id=self.device_1.pk),
            relationship=self.relationship_3,
        )

    def test_update_relationship_associations_valid_2(self):
        """
        An existing record with an existing ONE_TO_ONE association can change its source.
        """
        # Existing ONE_TO_ONE relation
        RelationshipAssociation(
            relationship=self.relationship_1,
            source_type=self.relationship_1.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_1.destination_type,
            destination_id=self.ipaddress_1.pk,
        ).validated_save()

        form = IPAddressForm(
            instance=self.ipaddress_1,
            data={
                "address": self.ipaddress_1.address,
                "status": self.ipaddress_status,
                "type": IPAddressTypeChoices.TYPE_HOST,
                "namespace": self.namespace.pk,
                f"cr_{self.relationship_1.key}__source": self.device_2.pk,
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
        RelationshipAssociation(
            relationship=self.relationship_2,
            source_type=self.relationship_2.source_type,
            source_id=self.device_1.pk,
            destination_type=self.relationship_2.destination_type,
            destination_id=self.vlangroup_1.pk,
        ).validated_save()

        form = VLANGroupForm(
            instance=self.vlangroup_1,
            data={
                "name": self.vlangroup_1.name,
                "location": self.location,
                f"cr_{self.relationship_2.key}__source": self.device_2.pk,
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

    def test_update_relationship_associations_valid_4(self):
        """
        An existing record with an existing ONE_TO_ONE_SYMMETRIC association can change its peer.

        This differs from test_update_relationship_associations_valid_1 in that the existing association has this
        record as the destination rather than the source, which *should* work either way.
        """
        # Existing ONE_TO_ONE_SYMMETRIC relation
        RelationshipAssociation(
            relationship=self.relationship_3,
            source_type=self.relationship_3.source_type,
            source_id=self.device_3.pk,
            destination_type=self.relationship_3.destination_type,
            destination_id=self.device_1.pk,
        ).validated_save()

        form = DeviceForm(
            instance=self.device_1,
            data={
                "location": self.location,
                "role": self.device_role,
                "device_type": self.device_type,
                "status": self.device_status,
                f"cr_{self.relationship_3.key}__peer": self.device_2.pk,
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.save())

        # Existing ONE_TO_ONE_SYMMETRIC relation should have been deleted and replaced
        with self.assertRaises(RelationshipAssociation.DoesNotExist):
            RelationshipAssociation.objects.get(relationship=self.relationship_3, source_id=self.device_3.pk)
        RelationshipAssociation.objects.get(
            Q(source_id=self.device_1.pk, destination_id=self.device_2.pk)
            | Q(source_id=self.device_2.pk, destination_id=self.device_1.pk),
            relationship=self.relationship_3,
        )

    def test_update_relationship_associatioins_invalid_1(self):
        """
        A record CANNOT form a relationship to itself.
        """
        form = DeviceForm(
            instance=self.device_1,
            data={
                "location": self.location,
                "role": self.device_role,
                "device_type": self.device_type,
                "status": self.device_status,
                f"cr_{self.relationship_3.key}__peer": self.device_1.pk,
            },
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            "Object Device 1 cannot form a relationship to itself!",
            form.errors[f"cr_{self.relationship_3.key}__peer"][0],
        )


class RelationshipModelBulkEditFormMixinTestCase(TestCase):
    """
    Test RelationshipModelBulkEditFormMixin validation and saving.
    """

    @classmethod
    def setUpTestData(cls):
        status = Status.objects.get_for_model(ipam_models.IPAddress).first()
        prefix_status = Status.objects.get_for_model(ipam_models.Prefix).first()
        cls.locations = dcim_models.Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]
        namespace = ipam_models.Namespace.objects.create(name="test_forms RelationshipModelBulkEditFormMixinTestCase")
        ipam_models.Prefix.objects.create(prefix="10.0.0.0/8", status=prefix_status, namespace=namespace)
        cls.ipaddresses = [
            ipam_models.IPAddress.objects.create(address="10.1.1.1/24", status=status, namespace=namespace),
            ipam_models.IPAddress.objects.create(address="10.2.2.2/24", status=status, namespace=namespace),
        ]

        cls.rel_1to1 = Relationship(
            label="Primary IP Address",
            key="primary_ip_address",
            source_type=ContentType.objects.get_for_model(dcim_models.Location),
            destination_type=ContentType.objects.get_for_model(ipam_models.IPAddress),
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        cls.rel_1to1.validated_save()

        cls.rel_1tom = Relationship(
            label="Addresses per location",
            key="addresses_per_location",
            source_type=ContentType.objects.get_for_model(dcim_models.Location),
            destination_type=ContentType.objects.get_for_model(ipam_models.IPAddress),
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )
        cls.rel_1tom.validated_save()

        cls.rel_mtom = Relationship(
            label="Multiplexing",
            key="multiplexing",
            source_type=ContentType.objects.get_for_model(dcim_models.Location),
            destination_type=ContentType.objects.get_for_model(ipam_models.IPAddress),
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        cls.rel_mtom.validated_save()

        cls.rel_mtom_s = Relationship(
            label="Peer Locations",
            key="peer_locations",
            source_type=ContentType.objects.get_for_model(dcim_models.Location),
            destination_type=ContentType.objects.get_for_model(dcim_models.Location),
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
        )
        cls.rel_mtom_s.validated_save()

    def test_location_form_rendering(self):
        form = LocationBulkEditForm(dcim_models.Location)
        self.assertEqual(
            set(form.relationships),
            {
                "cr_addresses_per_location__destination",
                "cr_multiplexing__destination",
                "cr_peer_locations__peer",
                "cr_primary_ip_address__destination",
            },
        )

        # One-to-many relationship is nullable but not editable
        self.assertIn("cr_addresses_per_location__destination", form.fields)
        self.assertTrue(form.fields["cr_addresses_per_location__destination"].disabled)
        self.assertIn("cr_addresses_per_location__destination", form.nullable_fields)

        # Many-to-many relationship has add/remove fields but is not directly editable or nullable
        self.assertNotIn("cr_multiplexing__destination", form.fields)
        self.assertIn("add_cr_multiplexing__destination", form.fields)
        self.assertIn("remove_cr_multiplexing__destination", form.fields)
        self.assertNotIn("cr_multiplexing__destination", form.nullable_fields)

        # Symmetric many-to-many relationship has add/remove fields but is not directly editable or nullable
        self.assertNotIn("cr_peer_locations__peer", form.fields)
        self.assertIn("add_cr_peer_locations__peer", form.fields)
        self.assertIn("remove_cr_peer_locations__peer", form.fields)
        self.assertNotIn("cr_peer_locations__peer", form.nullable_fields)

        # One-to-one relationship is nullable but not editable
        self.assertIn("cr_primary_ip_address__destination", form.fields)
        self.assertTrue(form.fields["cr_primary_ip_address__destination"].disabled)
        self.assertIn("cr_primary_ip_address__destination", form.nullable_fields)

    def test_ipaddress_form_rendering(self):
        form = IPAddressBulkEditForm(ipam_models.IPAddress)
        self.assertEqual(
            set(form.relationships),
            {
                "cr_addresses_per_location__source",
                "cr_multiplexing__source",
                "cr_primary_ip_address__source",
            },
        )

        # Many-to-one relationship is editable and nullable
        self.assertIn("cr_addresses_per_location__source", form.fields)
        self.assertIn("cr_addresses_per_location__source", form.nullable_fields)

        # Many-to-many relationship has add/remove fields but is not directly editable or nullable
        self.assertNotIn("cr_multiplexing__source", form.fields)
        self.assertIn("add_cr_multiplexing__source", form.fields)
        self.assertIn("remove_cr_multiplexing__source", form.fields)
        self.assertNotIn("cr_multiplexing__source", form.nullable_fields)

        # One-to-one relationship is nullable but not editable
        self.assertIn("cr_primary_ip_address__source", form.fields)
        self.assertTrue(form.fields["cr_primary_ip_address__source"].disabled)
        self.assertIn("cr_primary_ip_address__source", form.nullable_fields)

    def test_location_form_nullification(self):
        """Test nullification of existing relationship-associations."""
        RelationshipAssociation.objects.create(
            relationship=self.rel_1to1,
            source=self.locations[0],
            destination=self.ipaddresses[0],
        )
        RelationshipAssociation.objects.create(
            relationship=self.rel_1to1,
            source=self.locations[1],
            destination=self.ipaddresses[1],
        )
        RelationshipAssociation.objects.create(
            relationship=self.rel_1tom,
            source=self.locations[0],
            destination=self.ipaddresses[0],
        )
        RelationshipAssociation.objects.create(
            relationship=self.rel_1tom,
            source=self.locations[0],
            destination=self.ipaddresses[1],
        )

        form = LocationBulkEditForm(
            model=dcim_models.Location, data={"pks": [location.pk for location in self.locations]}
        )
        form.is_valid()
        form.save_relationships(
            instance=self.locations[0],
            nullified_fields=["cr_primary_ip_address__destination", "cr_addresses_per_location__destination"],
        )
        form.save_relationships(
            instance=self.locations[1],
            nullified_fields=["cr_primary_ip_address__destination", "cr_addresses_per_location__destination"],
        )

        self.assertEqual(0, RelationshipAssociation.objects.count())

    def test_location_form_add_mtom(self):
        """Test addition of relationship-associations for many-to-many relationships."""
        form = LocationBulkEditForm(
            model=dcim_models.Location,
            data={
                "pks": [self.locations[0].pk],
                "add_cr_multiplexing__destination": [ipaddress.pk for ipaddress in self.ipaddresses],
                "add_cr_peer_locations__peer": [self.locations[1].pk],
            },
        )
        form.is_valid()
        form.save_relationships(instance=self.locations[0], nullified_fields=[])

        ras = RelationshipAssociation.objects.filter(relationship=self.rel_mtom, source_id=self.locations[0].pk)
        self.assertEqual(2, ras.count())
        ras = RelationshipAssociation.objects.filter(relationship=self.rel_mtom_s)
        self.assertEqual(1, ras.count())

    def test_location_form_remove_mtom(self):
        """Test removal of relationship-associations for many-to-many relationships."""
        RelationshipAssociation.objects.create(
            relationship=self.rel_mtom,
            source=self.locations[0],
            destination=self.ipaddresses[0],
        )
        RelationshipAssociation.objects.create(
            relationship=self.rel_mtom,
            source=self.locations[0],
            destination=self.ipaddresses[1],
        )
        RelationshipAssociation.objects.create(
            relationship=self.rel_mtom,
            source=self.locations[1],
            destination=self.ipaddresses[0],
        )
        RelationshipAssociation.objects.create(
            relationship=self.rel_mtom,
            source=self.locations[1],
            destination=self.ipaddresses[1],
        )
        RelationshipAssociation.objects.create(
            relationship=self.rel_mtom_s,
            source=self.locations[0],
            destination=self.locations[1],
        )
        form = LocationBulkEditForm(
            model=dcim_models.Location,
            data={
                "pks": [self.locations[0].pk, self.locations[1].pk],
                "remove_cr_multiplexing__destination": [self.ipaddresses[0].pk],
                "remove_cr_peer_locations__peer": [self.locations[0].pk, self.locations[1].pk],
            },
        )
        form.is_valid()
        form.save_relationships(instance=self.locations[0], nullified_fields=[])
        form.save_relationships(instance=self.locations[1], nullified_fields=[])

        ras = RelationshipAssociation.objects.filter(relationship=self.rel_mtom)
        self.assertEqual(2, ras.count())
        for ra in ras:
            self.assertEqual(self.ipaddresses[1], ra.destination)

        ras = RelationshipAssociation.objects.filter(relationship=self.rel_mtom_s)
        self.assertEqual(0, ras.count())

    def test_ipaddress_form_add_mto1(self):
        """Test addition of relationship-associations for many-to-one relationships."""
        form = IPAddressBulkEditForm(
            model=ipam_models.IPAddress,
            data={
                "pks": [self.ipaddresses[0].pk],
                "cr_addresses_per_location__source": self.locations[0].pk,
            },
        )
        form.is_valid()
        form.save_relationships(instance=self.ipaddresses[0], nullified_fields=[])

        ras = RelationshipAssociation.objects.filter(relationship=self.rel_1tom)
        self.assertEqual(1, ras.count())


class WebhookFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        console_port_content_type = ContentType.objects.get_for_model(dcim_models.ConsolePort)
        location_content_type = ContentType.objects.get_for_model(dcim_models.Location)
        url = "http://example.com/test"

        webhook = Webhook.objects.create(
            name="webhook-1",
            enabled=True,
            type_create=True,
            type_update=True,
            type_delete=False,
            payload_url=url,
            http_method="POST",
            http_content_type="application/json",
        )
        webhook.content_types.add(console_port_content_type)

        cls.webhooks_data = [
            {
                "name": "webhook-2",
                "content_types": [location_content_type.pk],
                "enabled": True,
                "type_create": True,
                "type_update": False,
                "type_delete": False,
                "payload_url": url,
                "http_method": "POST",
                "http_content_type": "application/json",
            },
            {
                "name": "webhook-3",
                "content_types": [console_port_content_type.pk],
                "enabled": True,
                "type_create": False,
                "type_update": False,
                "type_delete": True,
                "payload_url": url,
                "http_method": "POST",
                "http_content_type": "application/json",
            },
            {
                "name": "webhook-4",
                "content_types": [console_port_content_type.pk],
                "enabled": True,
                "type_create": True,
                "type_update": True,
                "type_delete": True,
                "payload_url": url,
                "http_method": "POST",
                "http_content_type": "application/json",
            },
        ]

    def test_create_webhooks_with_diff_content_type_same_url_same_action(self):
        """
        Create a new webhook with different content_types, same url and same action with a webhook that exists

        Example:
            Webhook 1: dcim | console port, create, update, http://localhost
            Webhook 2: dcim | location, create, http://localhost
        """
        form = WebhookForm(data=self.webhooks_data[0])

        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(Webhook.objects.filter(name=self.webhooks_data[0]["name"]).count(), 1)

    def test_create_webhooks_with_same_content_type_same_url_diff_action(self):
        """
        Create a new webhook with same content_types, same url and diff action with a webhook that exists

        Example:
            Webhook 1: dcim | console port, create, update, http://localhost
            Webhook 2: dcim | console port, delete, http://localhost
        """
        form = WebhookForm(data=self.webhooks_data[1])

        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(Webhook.objects.filter(name=self.webhooks_data[1]["name"]).count(), 1)

    def test_create_webhooks_with_same_content_type_same_url_common_action(self):
        """
        Create a new webhook with same content_types, same url and common action with a webhook that exists

        Example:
            Webhook 1: dcim | console port, create, update, http://localhost
            Webhook 2: dcim | console port, create, update, delete, http://localhost
        """
        form = WebhookForm(data=self.webhooks_data[2])

        self.assertFalse(form.is_valid())
        error_msg = json.loads(form.errors.as_json())

        self.assertEqual(Webhook.objects.filter(name=self.webhooks_data[2]["name"]).count(), 0)
        self.assertIn("type_create", error_msg)
        self.assertEqual(
            error_msg["type_create"][0]["message"],
            "A webhook already exists for create on dcim | console port to URL http://example.com/test",
        )
        self.assertEqual(
            error_msg["type_update"][0]["message"],
            "A webhook already exists for update on dcim | console port to URL http://example.com/test",
        )


class DeprecatedAliasesTestCase(TestCase):
    """Test that deprecated class names still exist, but report a DeprecationWarning when used."""

    def test_deprecated_form_mixin_classes(self):
        # Importing these mixin classes doesn't directly warn, but subclassing them does.
        from nautobot.extras.forms import (
            AddRemoveTagsForm,
            CustomFieldBulkEditForm,
            CustomFieldBulkCreateForm,
            CustomFieldFilterForm,
            CustomFieldModelForm,
            RelationshipModelForm,
            StatusBulkEditFormMixin,
            StatusFilterFormMixin,
        )

        for deprecated_form_class, replacement_form_class in (
            (AddRemoveTagsForm, TagsBulkEditFormMixin),
            (CustomFieldBulkEditForm, CustomFieldModelBulkEditFormMixin),
            (CustomFieldBulkCreateForm, CustomFieldModelBulkEditFormMixin),
            (CustomFieldFilterForm, CustomFieldModelFilterFormMixin),
            (CustomFieldModelForm, CustomFieldModelFormMixin),
            (RelationshipModelForm, RelationshipModelFormMixin),
            (StatusBulkEditFormMixin, StatusModelBulkEditFormMixin),
            (StatusFilterFormMixin, StatusModelFilterFormMixin),
        ):
            with self.subTest(msg=f"Replace {deprecated_form_class.__name__} with {replacement_form_class.__name__}"):
                # Subclassing the deprecated class should raise a DeprecationWarning
                with warnings.catch_warnings(record=True) as warn_list:
                    # Ensure that warnings are always triggered
                    warnings.simplefilter("always")

                    class MyForm(deprecated_form_class):  # pylint: disable=unused-variable
                        pass

                    self.assertEqual(len(warn_list), 1)
                    warning = warn_list[0]
                    self.assertTrue(issubclass(warning.category, DeprecationWarning))
                    self.assertIn(f"{deprecated_form_class.__name__} is deprecated", str(warning))
                    self.assertIn(f"Instead of deriving MyForm from {deprecated_form_class.__name__}", str(warning))
                    self.assertIn(f"inherit from class {replacement_form_class.__name__} instead", str(warning))

                # Subclassing the replacement class should not warn
                with warnings.catch_warnings(record=True) as warn_list:
                    # Ensure that warnings are always triggered
                    warnings.simplefilter("always")

                    class MyBetterForm(replacement_form_class):  # pylint: disable=unused-variable
                        pass

                    self.assertEqual(len(warn_list), 0)


class JobEditFormTestCase(TestCase):
    def test_update_job_with_approval_required_and_has_has_sensitive_variables_is_true(self):
        form_data = {
            "grouping_override": True,
            "grouping": "Overridden grouping",
            "name_override": True,
            "name": "Overridden name",
            "description_override": True,
            "description": "This is an overridden description.",
            "enabled": True,
            "approval_required_override": True,
            "approval_required": True,
            "dryrun_default_override": True,
            "dryrun_default": True,
            "hidden_override": True,
            "hidden": True,
            "soft_time_limit_override": True,
            "soft_time_limit": 350.1,
            "time_limit_override": True,
            "time_limit": 650,
            "has_sensitive_variables": True,
            "has_sensitive_variables_override": True,
            "task_queues": [],
            "task_queues_override": True,
        }
        form = JobEditForm(data=form_data)

        self.assertFalse(form.is_valid())
        error_msg = json.loads(form.errors.as_json())
        self.assertEqual(
            error_msg["approval_required"][0]["message"],
            "A job that may have sensitive variables cannot be marked as requiring approval",
        )


class ConfigContextFormTestCase(TestCase):
    @override_settings(CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED=True)
    def test_with_dynamic_groups(self):
        """Asserts that `ConfigContextForm.dynamic_group` is present when feature flag is enabled."""
        form = ConfigContextForm()
        self.assertIn("dynamic_groups", form.fields)

    @override_settings(CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED=False)
    def test_without_dynamic_groups(self):
        """Asserts that `ConfigContextForm.dynamic_group` is NOT present when feature flag is disabled."""
        form = ConfigContextForm()
        self.assertNotIn("dynamic_groups", form.fields)


class ConfigContextFilterFormTestCase(TestCase):
    @override_settings(CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED=True)
    def test_with_dynamic_groups(self):
        """Asserts that `ConfigContextForm.dynamic_group` is present when feature flag is enabled."""
        context_filter_form = ConfigContextFilterForm()
        self.assertIn("dynamic_groups", context_filter_form.fields)

    @override_settings(CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED=False)
    def test_without_dynamic_groups(self):
        """Asserts that `ConfigContextFilterForm.dynamic_group` is NOT present when feature flag is disabled."""
        context_filter_form = ConfigContextFilterForm()
        self.assertNotIn("dynamic_groups", context_filter_form.fields)


class CustomFieldModelFormMixinTestCase(TestCase):
    def test_custom_field_data_removed_in_all(self):
        """Asserts that when `__all__` is set on a CustomFieldModelFormMixin, _custom_field_data is stripped."""

        class TestForm(CustomFieldModelFormMixin):
            class Meta:
                model = dcim_models.InterfaceRedundancyGroup
                fields = "__all__"

        custom_field_form = TestForm()
        self.assertNotIn("_custom_field_data", custom_field_form.fields)

    def test_custom_field_data_kept_if_explicit(self):
        """Asserts that _custom_field_data will still show up if explicitly set."""

        class TestForm(CustomFieldModelFormMixin):
            class Meta:
                model = dcim_models.InterfaceRedundancyGroup
                fields = ["_custom_field_data"]

        custom_field_form = TestForm()
        self.assertIn("_custom_field_data", custom_field_form.fields)
