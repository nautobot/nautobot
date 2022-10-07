from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from netaddr import IPAddress, IPNetwork

from nautobot.dcim.models import DeviceRole

from .example_jobs.script_variables import (
    BooleanVarScript,
    ChoiceVarScript,
    FileVarScript,
    IntegerVarScript,
    IPAddressVarScript,
    IPAddressWithMaskVarScript,
    IPNetworkVarScript,
    MultiChoiceVarScript,
    MultiObjectVarScript,
    ObjectVarScript,
    StringVarScript,
    TextVarScript,
)


class ScriptVariablesTest(TestCase):
    def test_stringvar(self):
        # Validate min_length enforcement
        data = {"var1": "xx"}
        form = StringVarScript().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate max_length enforcement
        data = {"var1": "xxxx"}
        form = StringVarScript().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate regex enforcement
        data = {"var1": "ABC"}
        form = StringVarScript().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate valid data
        data = {"var1": "abc"}
        form = StringVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], data["var1"])

    def test_textvar(self):
        # Validate valid data
        data = {"var1": "This is a test string"}
        form = TextVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], data["var1"])

    def test_integervar(self):
        # Validate min_value enforcement
        data = {"var1": 4}
        form = IntegerVarScript().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate max_value enforcement
        data = {"var1": 11}
        form = IntegerVarScript().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate valid data
        data = {"var1": 7}
        form = IntegerVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], data["var1"])

    def test_booleanvar(self):
        # Validate True
        data = {"var1": True}
        form = BooleanVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], True)

        # Validate False
        data = {"var1": False}
        form = BooleanVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], False)

    def test_choicevar(self):
        # Validate valid choice
        data = {"var1": "ff0000"}
        form = ChoiceVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], "ff0000")

        # Validate invalid choice
        data = {"var1": "taupe"}
        form = ChoiceVarScript().as_form(data)
        self.assertFalse(form.is_valid())

    def test_multichoicevar(self):
        # Validate single choice
        data = {"var1": ["ff0000"]}
        form = MultiChoiceVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], ["ff0000"])

        # Validate multiple choices
        data = {"var1": ("ff0000", "00ff00")}
        form = MultiChoiceVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], ["ff0000", "00ff00"])

        # Validate invalid choice
        data = {"var1": "taupe"}
        form = MultiChoiceVarScript().as_form(data)
        self.assertFalse(form.is_valid())

    def test_objectvar(self):
        # Populate some objects
        for i in range(1, 6):
            DeviceRole(name=f"Device Role {i}", slug=f"device-role-{i}").save()

        # Validate valid data
        data = {"var1": DeviceRole.objects.first().pk}
        form = ObjectVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"].pk, data["var1"])

    def test_multiobjectvar(self):
        # Populate some objects
        for i in range(1, 6):
            DeviceRole(name=f"Device Role {i}", slug=f"device-role-{i}").save()

        # Validate valid data
        data = {"var1": [role.pk for role in DeviceRole.objects.all()[:3]]}
        form = MultiObjectVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"][0].pk, data["var1"][0])
        self.assertEqual(form.cleaned_data["var1"][1].pk, data["var1"][1])
        self.assertEqual(form.cleaned_data["var1"][2].pk, data["var1"][2])

    def test_filevar(self):
        # Test file
        testfile = SimpleUploadedFile(name="test_file.txt", content=b"This is an test file for testing")

        # Validate valid data
        file_data = {"var1": testfile}
        form = FileVarScript().as_form(data=None, files=file_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], testfile)

    def test_ipaddressvar(self):
        # Validate IP network enforcement
        data = {"var1": "1.2.3"}
        form = IPAddressVarScript().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate IP mask exclusion
        data = {"var1": "192.0.2.0/24"}
        form = IPAddressVarScript().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate valid data
        data = {"var1": "192.0.2.1"}
        form = IPAddressVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], IPAddress(data["var1"]))

    def test_ipaddresswithmaskvar(self):
        # Validate IP network enforcement
        data = {"var1": "1.2.3"}
        form = IPAddressWithMaskVarScript().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate IP mask requirement
        data = {"var1": "192.0.2.0"}
        form = IPAddressWithMaskVarScript().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate valid data
        data = {"var1": "192.0.2.0/24"}
        form = IPAddressWithMaskVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], IPNetwork(data["var1"]))

    def test_ipnetworkvar(self):
        # Validate IP network enforcement
        data = {"var1": "1.2.3"}
        form = IPNetworkVarScript().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate host IP check
        data = {"var1": "192.0.2.1/24"}
        form = IPNetworkVarScript().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)

        # Validate valid data
        data = {"var1": "192.0.2.0/24"}
        form = IPNetworkVarScript().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], IPNetwork(data["var1"]))
