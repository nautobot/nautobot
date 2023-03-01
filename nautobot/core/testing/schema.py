from io import StringIO
import yaml

from django.conf import settings
from django.core.management import call_command
from django.test import tag

from nautobot.core.testing import views


@tag("unit")
class OpenAPISchemaTestCases:
    class BaseSchemaTestCase(views.TestCase):
        """Base class for testing of the OpenAPI schema."""

        @classmethod
        def setUpTestData(cls):
            # We could load the schema from the /api/swagger.yaml endpoint in setUp(self) via self.client,
            # but it's fairly expensive to do so. Better to do so only once per class.
            cls.schemas = {}
            for api_version in settings.REST_FRAMEWORK_ALLOWED_VERSIONS:
                out = StringIO()
                err = StringIO()
                call_command("spectacular", "--api-version", api_version, stdout=out, stderr=err)
                cls.schemas[api_version] = yaml.safe_load(out.getvalue())
