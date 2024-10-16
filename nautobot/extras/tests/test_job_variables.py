from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from nautobot.dcim.models import Device
from nautobot.extras.jobs import (
    BooleanVar,
    ChoiceVar,
    FileVar,
    IntegerVar,
    IPAddressVar,
    IPAddressWithMaskVar,
    IPNetworkVar,
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
        field = StringVar(min_length=3, max_length=3, regex=r"[a-z]+").as_field()

        # Validate min_length enforcement
        with self.assertRaises(ValidationError) as cm:
            field.clean("xx")
        self.assertIn("Ensure this value has at least 3 characters (it has 2).", str(cm.exception))

        # Validate max_length enforcement
        with self.assertRaises(ValidationError) as cm:
            field.clean("xxxx")
        self.assertIn("Ensure this value has at most 3 characters (it has 4).", str(cm.exception))

        # Validate regex enforcement
        with self.assertRaises(ValidationError) as cm:
            field.clean("ABC")
        self.assertIn("Invalid value. Must match regex: [a-z]+'", str(cm.exception))

        # Validate valid data
        field.clean("abc")

    def test_textvar(self):
        field = TextVar().as_field()

        # Validate valid data
        field.clean("This is a test string")

    def test_integervar(self):
        field = IntegerVar(min_value=5, max_value=10).as_field()

        # Validate min_value enforcement
        with self.assertRaises(ValidationError) as cm:
            field.clean(4)
        self.assertIn("Ensure this value is greater than or equal to 5.", str(cm.exception))

        # Validate max_value enforcement
        with self.assertRaises(ValidationError) as cm:
            field.clean(11)
        self.assertIn("Ensure this value is less than or equal to 10.", str(cm.exception))

        # Validate valid data
        field.clean(7)

    def test_booleanvar(self):
        field = BooleanVar().as_field()

        # Validate True
        field.clean(True)

        # Validate False
        field.clean(False)

    def test_choicevar(self):
        field = ChoiceVar(choices=CHOICES).as_field()

        # Validate valid choice
        field.clean("ff0000")

        # Validate invalid choice
        with self.assertRaises(ValidationError) as cm:
            field.clean("taupe")
        self.assertIn("Select a valid choice. taupe is not one of the available choices.", str(cm.exception))

    def test_multichoicevar(self):
        field = MultiChoiceVar(choices=CHOICES).as_field()

        # Validate valid choice
        field.clean(["ff0000"])

        # Validate multiple choices
        field.clean(("ff0000", "00ff00"))

        # Validate invalid choice
        with self.assertRaises(ValidationError) as cm:
            field.clean(["taupe"])
        self.assertIn("Select a valid choice. taupe is not one of the available choices.", str(cm.exception))

    def test_objectvar(self):
        field = ObjectVar(model=Role).as_field()

        # Validate valid data
        field.clean(Role.objects.get_for_model(Device).first().pk)

    def test_multiobjectvar(self):
        field = MultiObjectVar(model=Role).as_field()

        # Validate valid data
        field.clean([role.pk for role in Role.objects.all()[:3]])

    def test_filevar(self):
        field = FileVar().as_field()

        # Test file
        testfile = SimpleUploadedFile(name="test_file.txt", content=b"This is an test file for testing")
        # Validate valid data
        field.clean(testfile)

    def test_ipaddressvar(self):
        field = IPAddressVar().as_field()

        # Validate IP network enforcement
        with self.assertRaises(ValidationError) as cm:
            field.clean("1.2.3")
        self.assertIn("Invalid IPv4/IPv6 address format: 1.2.3", str(cm.exception))

        # Validate IP mask exclusion
        with self.assertRaises(ValidationError) as cm:
            field.clean("192.0.2.0/24")
        self.assertIn("Invalid IPv4/IPv6 address format: 192.0.2.0/24", str(cm.exception))

        # Validate valid data
        field.clean("192.0.2.1")

    def test_ipaddresswithmaskvar(self):
        field = IPAddressWithMaskVar().as_field()

        # Validate IP network enforcement
        with self.assertRaises(ValidationError) as cm:
            field.clean("1.2.3")
        self.assertIn("CIDR mask (e.g. /24) is required.", str(cm.exception))

        # Validate IP mask requirement
        with self.assertRaises(ValidationError) as cm:
            field.clean("192.0.2.0")
        self.assertIn("CIDR mask (e.g. /24) is required.", str(cm.exception))

        # Validate valid data
        field.clean("192.0.2.0/24")

    def test_ipnetworkvar(self):
        field = IPNetworkVar().as_field()

        # Validate IP network enforcement
        with self.assertRaises(ValidationError) as cm:
            field.clean("1.2.3")
        self.assertIn("CIDR mask (e.g. /24) is required.", str(cm.exception))

        # Validate host IP check
        with self.assertRaises(ValidationError) as cm:
            field.clean("192.0.2.1/24")
        self.assertIn("192.0.2.1/24 is not a valid prefix. Did you mean 192.0.2.0/24?", str(cm.exception))

        # Validate valid data
        field.clean("192.0.2.0/24")

    def test_jsonvar(self):
        field = JSONVar().as_field()

        # Valid JSON value as dictionary
        field.clean({"key1": "value1"})

        # Valid JSON value as jsonified dictionary
        field.clean('{"key1": "value1"}')

        # Invalid JSON value
        with self.assertRaises(ValidationError) as cm:
            field.clean('{"key1": True}')
        self.assertIn("Enter a valid JSON.", str(cm.exception))
