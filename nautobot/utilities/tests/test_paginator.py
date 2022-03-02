"""Test the nautobot.utilities.paginator module."""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from constance.test import override_config

from nautobot.utilities.paginator import get_paginate_count


class PaginatorTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(username="User 1", is_active=True)
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get("some_paginated_view")
        self.request.user = self.user

    @override_config(PAGINATE_COUNT=100)
    def test_get_paginate_count_config(self):
        """Get the default paginate count from Constance config."""
        self.assertEqual(get_paginate_count(self.request), 100)

    @override_settings(PAGINATE_COUNT=50)
    @override_config(PAGINATE_COUNT=100)
    def test_get_paginate_count_settings(self):
        """Get the default paginate count from Django settings, overriding Constance config."""
        self.assertEqual(get_paginate_count(self.request), 50)

    @override_settings(PAGINATE_COUNT=50)
    @override_config(PAGINATE_COUNT=100)
    def test_get_paginate_count_user_config(self):
        """Get the user's configured paginate count, overriding global defaults."""
        self.user.set_config("pagination.per_page", 200, commit=True)
        self.assertEqual(get_paginate_count(self.request), 200)

    @override_settings(PAGINATE_COUNT=50)
    @override_config(PAGINATE_COUNT=100)
    def test_get_paginate_count_request_params(self):
        """Get the paginate count from the request's GET params, overriding user and global default values."""
        self.user.set_config("pagination.per_page", 200, commit=True)
        request = self.request_factory.get("some_paginated_view", {"per_page": 400})
        request.user = self.user
        self.assertEqual(get_paginate_count(request), 400)
