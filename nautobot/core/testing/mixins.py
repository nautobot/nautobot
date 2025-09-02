import json
import warnings

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models import JSONField, ManyToManyField, ManyToManyRel
from django.forms.models import model_to_dict
from django.test.testcases import assert_and_parse_html
from django.test.utils import CaptureQueriesContext
from netaddr import IPNetwork
from rest_framework.test import APIClient, APIRequestFactory

from nautobot.core.models import fields as core_fields
from nautobot.core.testing import utils
from nautobot.core.utils import permissions
from nautobot.extras import management, models as extras_models
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.users import models as users_models

# Use the proper swappable User model
User = get_user_model()


class NautobotTestClient(APIClient):
    """
    Base client class for Nautobot testing.

    DO NOT USE THIS IN PRODUCTION NAUTOBOT CODE.
    """

    def __init__(self, *args, **kwargs):
        """
        Default the SERVER_NAME to "nautobot.example.com" rather than Django's default "testserver".

        This matches the ALLOWED_HOSTS set in nautobot/core/tests/nautobot_config.py and
        helps to protect us against issues like https://github.com/nautobot/nautobot/issues/3065.
        """
        kwargs.setdefault("SERVER_NAME", "nautobot.example.com")
        super().__init__(*args, **kwargs)


class NautobotTestCaseMixin:
    """Base class for all Nautobot-specific unit tests."""

    user_permissions = ()
    client_class = NautobotTestClient
    maxDiff = None

    def setUpNautobot(self, client=True, populate_status=False):
        """Setup shared testuser, statuses and client."""
        # Re-populate status choices after database truncation by TransactionTestCase
        if populate_status:
            management.populate_status_choices(apps, None)

        # Create the test user and assign permissions
        self.user = User.objects.create_user(username="nautobotuser")
        self.add_permissions(*self.user_permissions)

        if client:
            # Initialize the test client
            if not hasattr(self, "client") or self.client is None:
                self.client = self.client_class()

            # Force login explicitly with the first-available backend
            self.client.force_login(self.user)

    def tearDown(self):
        """
        Clear cache after each test case.

        In theory this shouldn't be necessary as our cache **should** appropriately update and clear itself when
        data changes occur, but in practice we've seen issues here. Best guess at present is that it's due to
        `TransactionTestCase` truncating the database, which presumably doesn't trigger the relevant Django signals
        that would otherwise refresh the cache appropriately.

        See also: https://code.djangoproject.com/ticket/11505
        """
        super().tearDown()
        cache.clear()

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
            if value and isinstance(field, (ManyToManyField, ManyToManyRel, core_fields.TagsField)):
                # Only convert ContentType to <app_label>.<model> for API serializers/views
                if api and field.related_model is ContentType:
                    model_dict[key] = sorted([f"{ct.app_label}.{ct.model}" for ct in value])
                # Otherwise always convert object instances to pk
                else:
                    if isinstance(field, ManyToManyRel):
                        value = value.all()
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
                if isinstance(field, core_fields.JSONArrayField):
                    model_dict[key] = ",".join([str(v) for v in value])

                # Convert JSONField dict values to JSON strings
                if isinstance(field, JSONField) and isinstance(value, dict):
                    model_dict[key] = json.dumps(value)

        return model_dict

    #
    # Permissions management
    #

    def add_permissions(self, *names, **kwargs):
        """
        Assign a set of permissions to the test user. Accepts permission names in the form <app>.<action>_<model>.
        Additional keyword arguments will be passed to the ObjectPermission constructor to allow creating more detailed permissions.

        Examples:
            >>> add_permissions("ipam.add_vlangroup", "ipam.view_vlangroup")
            >>> add_permissions("ipam.add_vlangroup", "ipam.view_vlangroup", constraints={"pk": "uuid-1234"})
        """
        for name in names:
            ct, action = permissions.resolve_permission_ct(name)
            obj_perm, _ = users_models.ObjectPermission.objects.get_or_create(name=name, actions=[action], **kwargs)
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ct)

    def remove_permissions(self, *names, **kwargs):
        """
        Remove a set of permissions. Accepts permission names in the form <app>.<action>_<model>.
        Additional keyword arguments will be passed to the ObjectPermission constructor to allow creating more detailed permissions.

        Examples:
            >>> remove_permissions("ipam.add_vlangroup", "ipam.view_vlangroup")
            >>> remove_permissions("ipam.add_vlangroup", "ipam.view_vlangroup", constraints={"pk": "uuid-1234"})
        """
        for name in names:
            _, action, _ = permissions.resolve_permission(name)
            try:
                obj_perm = users_models.ObjectPermission.objects.get(name=name, actions=[action], **kwargs)
                obj_perm.delete()
            except ObjectDoesNotExist:
                # Permission does not exist, so nothing to remove
                pass

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
            err_message = f"Expected HTTP status(es) {expected_status}; received {response.status_code}:"
            if hasattr(response, "data"):
                # REST API response; pass the response data through directly
                err_message += f"\n{response.data}"
            # Attempt to extract form validation errors from the response HTML
            elif form_errors := utils.extract_form_failures(response.content.decode(response.charset)):
                err_message += f"\n{form_errors}"
            elif body_content := utils.extract_page_body(response.content.decode(response.charset)):
                err_message += f"\n{body_content}"
            else:
                err_message += "No data"
            if msg:
                err_message = f"{msg}\n{err_message}"
        self.assertIn(response.status_code, expected_status, err_message)

    def assertJobResultStatus(self, job_result, expected_status=JobResultStatusChoices.STATUS_SUCCESS):
        """Assert that the given job_result has the expected_status, or print the job logs to aid in debugging."""
        self.assertEqual(
            job_result.status,
            expected_status,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )

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
            elif k == "data_schema" and isinstance(v, str):
                # Standardize the data_schema JSON, since the column is JSON and MySQL/dolt do not guarantee order
                new_model_dict[k] = self.standardize_json(v)
            elif hasattr(v, "all") and callable(v.all):
                # Convert related manager to list of PKs
                new_model_dict[k] = sorted(v.all().values_list("pk", flat=True))
            else:
                new_model_dict[k] = v

        # Omit any dictionary keys which are not instance attributes or have been excluded
        relevant_data = {}
        for k, v in data.items():
            if hasattr(instance, k) and k not in exclude:
                if isinstance(v, list):
                    # Sort lists of values. This includes items like tags, or other M2M fields
                    relevant_data[k] = sorted(v)
                elif k == "data_schema" and isinstance(v, str):
                    # Standardize the data_schema JSON, since the column is JSON and MySQL/dolt do not guarantee order
                    relevant_data[k] = self.standardize_json(v)
                elif hasattr(v, "all") and callable(v.all):
                    # Convert related manager to list of PKs
                    relevant_data[k] = sorted(v.all().values_list("pk", flat=True))
                else:
                    relevant_data[k] = v

        self.assertEqual(new_model_dict, relevant_data)

    def assertQuerysetEqualAndNotEmpty(self, qs, values, *args, **kwargs):
        """Wrapper for assertQuerysetEqual with additional logic to assert input queryset and values are not empty"""

        self.assertNotEqual(len(qs), 0, "Queryset cannot be empty")
        self.assertNotEqual(len(values), 0, "Values cannot be empty")

        return self.assertQuerysetEqual(qs, values, *args, **kwargs)

    class _AssertApproximateNumQueriesContext(CaptureQueriesContext):
        """Implementation class underlying the assertApproximateNumQueries decorator/context manager."""

        def __init__(self, test_case, minimum, maximum, connection):
            self.test_case = test_case
            self.minimum = minimum
            self.maximum = maximum
            super().__init__(connection)

        def __exit__(self, exc_type, exc_value, traceback):
            super().__exit__(exc_type, exc_value, traceback)
            if exc_type is not None:
                return
            num_queries = len(self)
            captured_queries_string = "\n".join(
                f"{i}. {query['sql']}" for i, query in enumerate(self.captured_queries, start=1)
            )
            self.test_case.assertGreaterEqual(
                num_queries,
                self.minimum,
                f"{num_queries} queries executed, but expected at least {self.minimum}.\n"
                f"Captured queries were:\n{captured_queries_string}",
            )
            self.test_case.assertLessEqual(
                num_queries,
                self.maximum,
                f"{num_queries} queries executed, but expected no more than {self.maximum}.\n"
                f"Captured queries were:\n{captured_queries_string}",
            )

    def assertApproximateNumQueries(self, minimum, maximum, func=None, *args, using=DEFAULT_DB_ALIAS, **kwargs):
        """Like assertNumQueries, but fuzzier. Assert that the number of queries falls within an acceptable range."""
        conn = connections[using]

        context = self._AssertApproximateNumQueriesContext(self, minimum, maximum, conn)
        if func is None:
            return context

        with context:
            func(*args, **kwargs)

        return None

    def assertBodyContains(self, response, text, count=None, status_code=200, msg_prefix="", html=False):
        """
        Like Django's `assertContains`, but uses `extract_page_body` utility function to scope the check more narrowly.

        Args:
            response (HttpResponse): The response to inspect
            text (str): Plaintext or HTML to check for in the response body
            count (int, optional): Number of times the `text` should occur, or None if we don't care as long as
                it's present at all.
            status_code (int): HTTP status code expected
            html (bool): If True, handle `text` as HTML, ignoring whitespace etc, as in Django's `assertHTMLEqual()`.
        """
        # The below is copied from SimpleTestCase._assert_contains and SimpleTestCase.assertContains
        # If the response supports deferred rendering and hasn't been rendered
        # yet, then ensure that it does get rendered before proceeding further.
        if hasattr(response, "render") and callable(response.render) and not response.is_rendered:
            response.render()

        if msg_prefix:
            msg_prefix += ": "

        self.assertHttpStatus(  # Nautobot-specific, original uses simple assertEqual()
            response, status_code, msg_prefix
        )

        if response.streaming:
            content = b"".join(response.streaming_content)
        else:
            content = response.content

        if not isinstance(text, bytes) or html:
            text = str(text)
            content = content.decode(response.charset)
            content = utils.extract_page_body(content)  # Nautobot-specific
            text_repr = f"'{text}'"
        else:
            text_repr = repr(text)

        if html:
            content = assert_and_parse_html(self, content, None, "Response's content is not valid HTML:")
            text = assert_and_parse_html(self, text, None, "Second argument is not valid HTML:")
        real_count = content.count(text)

        if count is not None:
            self.assertEqual(
                real_count,
                count,
                msg_prefix + f"Found {real_count} instances of {text_repr} in response (expected {count}):\n{content}",
            )
        else:
            self.assertTrue(real_count != 0, msg_prefix + f"Couldn't find {text_repr} in response:\n{content}")

    #
    # Convenience methods
    #

    def absolute_api_url(self, obj):
        """Get the absolute API URL ("http://nautobot.example.com/api/...") for a given object."""
        request = APIRequestFactory(SERVER_NAME="nautobot.example.com").get("")
        return request.build_absolute_uri(obj.get_absolute_url(api=True))

    def standardize_json(self, data):
        obj = json.loads(data)
        return json.dumps(obj, sort_keys=True)

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
        return [extras_models.Tag.objects.create(name=name) for name in names]
