from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from netaddr import IPAddress, IPNetwork

from nautobot.dcim.models import Device
from nautobot.extras.jobs import (
    BooleanVar,
    ChoiceVar,
    FileVar,
    IntegerVar,
    IPAddressVar,
    IPAddressWithMaskVar,
    IPNetworkVar,
    Job,
    JSONVar,
    MultiChoiceVar,
    MultiObjectVar,
    ObjectVar,
    StringVar,
    TextVar,
)
from nautobot.extras.models import Role

CHOICES = (("ff0000", "Red"), ("00ff00", "Green"), ("0000ff", "Blue"))


class JobVariablesTest(TestCase):
    def test_stringvar(self):
        class StringVarJob(Job):
            var1 = StringVar(min_length=3, max_length=3, regex=r"[a-z]+")

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
        class TextVarJob(Job):
            var1 = TextVar()

        # Validate valid data
        data = {"var1": "This is a test string"}
        form = TextVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], data["var1"])

    def test_integervar(self):
        class IntegerVarJob(Job):
            var1 = IntegerVar(min_value=5, max_value=10)

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
        class BooleanVarJob(Job):
            var1 = BooleanVar()

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
        class ChoiceVarJob(Job):
            var1 = ChoiceVar(choices=CHOICES)

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
        class MultiChoiceVarJob(Job):
            var1 = MultiChoiceVar(choices=CHOICES)

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
        class ObjectVarJob(Job):
            var1 = ObjectVar(model=Role)

        # Validate valid data
        data = {"var1": Role.objects.get_for_model(Device).first().pk}
        form = ObjectVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"].pk, data["var1"])

    def test_multiobjectvar(self):
        class MultiObjectVarJob(Job):
            var1 = MultiObjectVar(model=Role)

        # Validate valid data
        data = {"var1": [role.pk for role in Role.objects.all()[:3]]}
        form = MultiObjectVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"][0].pk, data["var1"][0])
        self.assertEqual(form.cleaned_data["var1"][1].pk, data["var1"][1])
        self.assertEqual(form.cleaned_data["var1"][2].pk, data["var1"][2])

    def test_filevar(self):
        class FileVarJob(Job):
            var1 = FileVar()

        # Test file
        testfile = SimpleUploadedFile(name="test_file.txt", content=b"This is an test file for testing")

        # Validate valid data
        file_data = {"var1": testfile}
        form = FileVarJob().as_form(data=None, files=file_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], testfile)

    def test_ipaddressvar(self):
        class IPAddressVarJob(Job):
            var1 = IPAddressVar()

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
        class IPAddressWithMaskVarJob(Job):
            var1 = IPAddressWithMaskVar()

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
        class IPNetworkVarJob(Job):
            var1 = IPNetworkVar()

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

    def test_jsonvar(self):
        class JSONVarJob(Job):
            var1 = JSONVar()

        # Valid JSON value as dictionary
        data = {"var1": {"key1": "value1"}}
        form = JSONVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], {"key1": "value1"})

        # Valid JSON value as jsonified dictionary
        data = {"var1": '{"key1": "value1"}'}
        form = JSONVarJob().as_form(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["var1"], {"key1": "value1"})

        # Invalid JSON value
        data = {"var1": '{"key1": True}'}
        form = JSONVarJob().as_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("var1", form.errors)
