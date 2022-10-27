import json
import warnings

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db.models import JSONField, ManyToManyField
from django.forms.models import model_to_dict
from django.test import Client
from django.utils.text import slugify
from netaddr import IPNetwork
from taggit.managers import TaggableManager

from nautobot.extras.management import populate_status_choices
from nautobot.extras.models import Tag
from nautobot.users.models import ObjectPermission
from nautobot.utilities.permissions import resolve_permission_ct
from nautobot.utilities.fields import JSONArrayField
from .utils import extract_form_failures


# Use the proper swappable User model
User = get_user_model()


class NautobotTestCaseMixin:
    """Base class for all Nautobot-specific unit tests."""

    user_permissions = ()

    def setUpNautobot(self, client=True, populate_status=False):
        """Setup shared testuser, statuses and client."""
        # Re-populate status choices after database truncation by TransactionTestCase
        if populate_status:
            populate_status_choices(apps, None)

        # Create the test user and assign permissions
        self.user = User.objects.create_user(username="nautobotuser")
        self.add_permissions(*self.user_permissions)

        if client:
            # Initialize the test client
            self.client = Client()

            # Force login explicitly with the first-available backend
            self.client.force_login(self.user)

    def prepare_instance(self, instance):
        """
        Test cases can override this method to perform any necessary manipulation of an instance prior to its evaluation
        against test data. For example, it can be used to decrypt a Secret's plaintext attribute.
        """
        return instance

    def model_to_dict(self, instance, fields, api=False):
        """
        Return a dictionary representation of an instance.
        """
        # Prepare the instance and call Django's model_to_dict() to extract all fields
        model_dict = model_to_dict(self.prepare_instance(instance), fields=fields)

        # Map any additional (non-field) instance attributes that were specified
        for attr in fields:
            if hasattr(instance, attr) and attr not in model_dict:
                model_dict[attr] = getattr(instance, attr)

        for key, value in list(model_dict.items()):
            try:
                field = instance._meta.get_field(key)
            except FieldDoesNotExist:
                # Attribute is not a model field, but may be a computed field,
                # so allow `field` checks to pass through.
                field = None

            # Handle ManyToManyFields
            if value and isinstance(field, (ManyToManyField, TaggableManager)):

                # Only convert ContentType to <app_label>.<model> for API serializers/views
                if api and field.related_model is ContentType:
                    model_dict[key] = sorted([f"{ct.app_label}.{ct.model}" for ct in value])
                # Otherwise always convert object instances to pk
                else:
                    model_dict[key] = sorted([obj.pk for obj in value])

            if api:

                # Replace ContentType primary keys with <app_label>.<model>
                if isinstance(getattr(instance, key), ContentType):
                    ct = ContentType.objects.get(pk=value)
                    model_dict[key] = f"{ct.app_label}.{ct.model}"

                # Convert IPNetwork instances to strings
                elif isinstance(value, IPNetwork):
                    model_dict[key] = str(value)

            else:

                # Convert ArrayFields to CSV strings
                if isinstance(field, JSONArrayField):
                    model_dict[key] = ",".join([str(v) for v in value])

                # Convert JSONField dict values to JSON strings
                if isinstance(field, JSONField) and isinstance(value, dict):
                    model_dict[key] = json.dumps(value)

        return model_dict

    #
    # Permissions management
    #

    def add_permissions(self, *names):
        """
        Assign a set of permissions to the test user. Accepts permission names in the form <app>.<action>_<model>.
        """
        for name in names:
            ct, action = resolve_permission_ct(name)
            obj_perm = ObjectPermission(name=name, actions=[action])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ct)

    #
    # Custom assertions
    #

    def assertHttpStatus(self, response, expected_status, msg=None):
        """
        TestCase method. Provide more detail in the event of an unexpected HTTP response.
        """
        err_message = None
        # Construct an error message only if we know the test is going to fail
        if isinstance(expected_status, int):
            expected_status = [expected_status]
        if response.status_code not in expected_status:
            if hasattr(response, "data"):
                # REST API response; pass the response data through directly
                err = response.data
            else:
                # Attempt to extract form validation errors from the response HTML
                form_errors = extract_form_failures(response.content.decode(response.charset))
                err = form_errors or response.content.decode(response.charset) or "No data"
            err_message = f"Expected HTTP status(es) {expected_status}; received {response.status_code}: {err}"
            if msg:
                err_message = f"{msg}\n{err_message}"
        self.assertIn(response.status_code, expected_status, err_message)

    def assertInstanceEqual(self, instance, data, exclude=None, api=False):
        """
        Compare a model instance to a dictionary, checking that its attribute values match those specified
        in the dictionary.

        :param instance: Python object instance
        :param data: Dictionary of test data used to define the instance
        :param exclude: List of fields to exclude from comparison (e.g. passwords, which get hashed)
        :param api: Set to True is the data is a JSON representation of the instance
        """
        if exclude is None:
            exclude = []

        fields = [k for k in data.keys() if k not in exclude]
        model_dict = self.model_to_dict(instance, fields=fields, api=api)

        new_model_dict = {}
        for k, v in model_dict.items():
            if isinstance(v, list):
                # Sort lists of values. This includes items like tags, or other M2M fields
                new_model_dict[k] = sorted(v)
            else:
                new_model_dict[k] = v

        # Omit any dictionary keys which are not instance attributes or have been excluded
        relevant_data = {}
        for k, v in data.items():
            if hasattr(instance, k) and k not in exclude:
                if isinstance(v, list):
                    # Sort lists of values. This includes items like tags, or other M2M fields
                    relevant_data[k] = sorted(v)
                else:
                    relevant_data[k] = v

        self.assertEqual(new_model_dict, relevant_data)

    def assertQuerysetEqualAndNotEmpty(self, qs, values, *args, **kwargs):
        """Wrapper for assertQuerysetEqual with additional logic to assert input queryset and values are not empty"""

        self.assertNotEqual(len(qs), 0, "Queryset cannot be empty")
        self.assertNotEqual(len(values), 0, "Values cannot be empty")

        return self.assertQuerysetEqual(qs, values, *args, **kwargs)

    #
    # Convenience methods
    #

    @classmethod
    def create_tags(cls, *names):
        """
        Create and return a Tag instance for each name given.

        DEPRECATED: use TagFactory instead.
        """
        warnings.warn(
            "create_tags() is deprecated and will be removed in a future Nautobot release. "
            "Use nautobot.extras.factory.TagFactory (provided in Nautobot 1.5 and later) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return [Tag.objects.create(name=name, slug=slugify(name)) for name in names]
