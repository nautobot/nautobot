from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from netaddr import IPAddress, IPNetwork

from nautobot.dcim.models import Device
from nautobot.extras.models import Role

from nautobot.extras.test_jobs.job_variables import (
    BooleanVarJob,
    ChoiceVarJob,
    FileVarJob,
    IntegerVarJob,
    IPAddressVarJob,
    IPAddressWithMaskVarJob,
    IPNetworkVarJob,
    MultiChoiceVarJob,
    MultiObjectVarJob,
    ObjectVarJob,
    StringVarJob,
    TextVarJob,
)


class JobVariablesTest(TestCase):
    def test_stringvar(self):
        # Validate min_length enforcement
        data = {"var1": "xx"}
        form = StringVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate max_length enforcement
        data = {"var1": "xxxx"}
        form = StringVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate regex enforcement
        data = {"var1": "ABC"}
        form = StringVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate valid data
        data = {"var1": "abc"}
        form = StringVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], data["var1"])

    def test_textvar(self):
        # Validate valid data
        data = {"var1": "This is a test string"}
        form = TextVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], data["var1"])

    def test_integervar(self):
        # Validate min_value enforcement
        data = {"var1": 4}
        form = IntegerVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate max_value enforcement
        data = {"var1": 11}
        form = IntegerVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate valid data
        data = {"var1": 7}
        form = IntegerVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], data["var1"])

    def test_booleanvar(self):
        # Validate True
        data = {"var1": True}
        form = BooleanVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], True)

        # Validate False
        data = {"var1": False}
        form = BooleanVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], False)

    def test_choicevar(self):
        # Validate valid choice
        data = {"var1": "ff0000"}
        form = ChoiceVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], "ff0000")

        # Validate invalid choice
        data = {"var1": "taupe"}
        form = ChoiceVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

    def test_multichoicevar(self):
        # Validate single choice
        data = {"var1": ["ff0000"]}
        form = MultiChoiceVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], ["ff0000"])

        # Validate multiple choices
        data = {"var1": ("ff0000", "00ff00")}
        form = MultiChoiceVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], ["ff0000", "00ff00"])

        # Validate invalid choice
        data = {"var1": "taupe"}
        form = MultiChoiceVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

    def test_objectvar(self):
        # Validate valid data
        data = {"var1": Role.objects.get_for_model(Device).first().pk}
        form = ObjectVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"].pk, data["var1"])

    def test_multiobjectvar(self):
        # Validate valid data
        data = {"var1": [role.pk for role in Role.objects.all()[:3]]}
        form = MultiObjectVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"][0].pk, data["var1"][0])
        self.assertEqual(form.cleaned_data["var1"][1].pk, data["var1"][1])
        self.assertEqual(form.cleaned_data["var1"][2].pk, data["var1"][2])

    def test_filevar(self):
        # Test file
        testfile = SimpleUploadedFile(name="test_file.txt", content=b"This is an test file for testing")

        # Validate valid data
        file_data = {"var1": testfile}
        form = FileVarJob().as_form(data=None, files=file_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], testfile)

    def test_ipaddressvar(self):
        # Validate IP network enforcement
        data = {"var1": "1.2.3"}
        form = IPAddressVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate IP mask exclusion
        data = {"var1": "192.0.2.0/24"}
        form = IPAddressVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate valid data
        data = {"var1": "192.0.2.1"}
        form = IPAddressVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], IPAddress(data["var1"]))

    def test_ipaddresswithmaskvar(self):
        # Validate IP network enforcement
        data = {"var1": "1.2.3"}
        form = IPAddressWithMaskVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate IP mask requirement
        data = {"var1": "192.0.2.0"}
        form = IPAddressWithMaskVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate valid data
        data = {"var1": "192.0.2.0/24"}
        form = IPAddressWithMaskVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], IPNetwork(data["var1"]))

    def test_ipnetworkvar(self):
        # Validate IP network enforcement
        data = {"var1": "1.2.3"}
        form = IPNetworkVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate host IP check
        data = {"var1": "192.0.2.1/24"}
        form = IPNetworkVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate valid data
        data = {"var1": "192.0.2.0/24"}
        form = IPNetworkVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], IPNetwork(data["var1"]))
