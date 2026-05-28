from unittest.mock import patch

from django.test import override_settings, RequestFactory
from django.urls import reverse
from rest_framework.response import Response

from nautobot.cloud.views import CloudResourceTypeUIViewSet
from nautobot.core.testing import TestCase
from nautobot.core.ui.titles import Titles
from nautobot.core.views.renderers import NautobotHTMLRenderer


class ObjectListViewTitlesTest(TestCase):
    """
    Test suite for verifying that Titles are correctly set in ObjectListView rendering.
    """

    user_permissions = ["cloud.view_cloudresourcetype"]

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    @override_settings(ALLOWED_HOSTS=["*"], PAGINATE_COUNT=5, MAX_PAGE_SIZE=10)
    def test_uiviewset_list_view_title(self):
        """
        Test that the list view title is correctly set from the Titles configuration.
        """

        path = reverse("cloud:cloudresourcetype_list")
        request = self.factory.get(path)
        request.user = self.user
        viewset_class = CloudResourceTypeUIViewSet
        with patch.object(CloudResourceTypeUIViewSet, "view_titles", Titles(titles={"list": "Burritos"})):
            view = viewset_class()
            view.action_map = {"get": "list"}

            request = view.initialize_request(request)

            view.setup(request)
            view.initial(request)

            renderer = NautobotHTMLRenderer()
            context = renderer.get_context(
                data={},
                accepted_media_type="text/html",
                renderer_context={"view": view, "request": request, "response": Response({})},
            )

            # Verify that the title is set in the context
            self.assertIn("view_titles", context)
            self.assertNotIn(
                "title", context
            )  # title is used within the render path but should not be directly in context
            self.assertEqual(context["view_titles"], viewset_class.view_titles)

            # Finally, render the view and verify the title appears in the response
            response = self.client.get(path)
            self.assertContains(response, "Burritos")
