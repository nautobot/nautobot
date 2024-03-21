import re

from django.test import tag
from django.urls import get_resolver, URLPattern, URLResolver

from nautobot.core.testing import TestCase


@tag("integration")
class AuthenticationEnforcedTestCase(TestCase):
    """
    Test that all* registered views require authentication to access.

    * with a very small number of known exceptions such as login and logout views.
    """

    def _get_url_patterns(self, patterns_list, path_so_far="/"):
        """Recursively yield a list of all registered URL paths."""
        for item in patterns_list:
            if isinstance(item, URLPattern):
                yield path_so_far + str(item.pattern)
            elif isinstance(item, URLResolver):
                # Recurse!
                yield from self._get_url_patterns(item.url_patterns, path_so_far=path_so_far + str(item.pattern))

    def _url_pattern_to_url(self, url_pattern):
        """Clean up url patterns into actual resolvable URLs."""
        url = url_pattern
        # Fixup tokens in path-style "classic" view URLs:
        # "/admin/users/user/<id>/password/"
        url = re.sub(r"<id>", "00000000-0000-0000-0000-000000000000", url)
        # "/silk/request/<uuid:request_id>/profile/<int:profile_id>/"
        url = re.sub(r"<int:\w+>", "1", url)
        # "/admin/admin/logentry/<path:object_id>/"
        url = re.sub(r"<path:\w+>", "1", url)
        # "/apps/installed-apps/<str:app>/"
        url = re.sub(r"<str:\w+>", "string", url)
        # "/dcim/locations/<uuid:pk>/"
        url = re.sub(r"<uuid:\w+>", "00000000-0000-0000-0000-000000000000", url)
        # tokens in regexp-style router urls, including REST and NautobotUIViewSet:
        # "/extras/^external-integrations/(?P<pk>[^/.]+)/$"
        # "/api/virtualization/^interfaces/(?P<pk>[^/.]+)/$"
        # "/api/virtualization/^interfaces/(?P<pk>[^/.]+)\\.(?P<format>[a-z0-9]+)/?$"
        url = re.sub(r"[$^]", "", url)
        url = re.sub(r"/\?", "/", url)
        url = re.sub(r"\(\?P<app_label>[^)]+\)", "users", url)
        url = re.sub(r"\(\?P<format>[^)]+\)", "json", url)
        url = re.sub(r"\(\?P<name>[^)]+\)", "string", url)
        url = re.sub(r"\(\?P<pk>[^)]+\)", "00000000-0000-0000-0000-000000000000", url)
        url = re.sub(r"\(\?P<url>[^)]+\)", "any", url)
        url = re.sub(r"\\", "", url)

        if any(char in url for char in "<>[]()?+^$"):
            self.fail(f"Unhandled token in URL {url}")

        return url

    def test_all_views_require_authentication(self):
        self.client.logout()
        resolver = get_resolver()
        url_patterns = self._get_url_patterns(resolver.url_patterns, path_so_far="/")

        for url_pattern in url_patterns:
            with self.subTest(url_pattern=url_pattern):
                url = self._url_pattern_to_url(url_pattern)
                response = self.client.get(url, follow=True)

                if response.status_code == 405:  # Method not allowed
                    response = self.client.post(url, follow=True)

                # Is a view that *should* be open to unauthenticated users?
                if url in [
                    "/admin/login/",
                    "/api/plugins/example-plugin/webhook/",
                    "/api/redoc/",
                    "/api/swagger/",
                    "/api/swagger.json",
                    "/api/swagger.yaml",
                    "/health/",
                    "/login/",
                    "/media-failure/",
                    "/template.css",
                ]:
                    self.assertHttpStatus(response, 200, msg=url)
                elif response.status_code == 200:
                    # UI views generally should redirect unauthenticated users to the appropriate login page
                    if url.startswith("/admin"):
                        if "logout" in url:
                            # /admin/logout/ sets next=/admin/ because having login redirect to logout would be silly
                            redirect_url = "/admin/login/?next=/admin/"
                        else:
                            redirect_url = f"/admin/login/?next={url}"
                    else:
                        if "logout" in url:
                            # /logout/ sets next=/ because having login redirect back to logout would be silly
                            redirect_url = "/login/?next=/"
                        else:
                            redirect_url = f"/login/?next={url}"
                    self.assertRedirects(response, redirect_url)
                elif response.status_code not in [403, 404]:
                    self.fail(
                        f"Unexpected {response.status_code} response at {url}: "
                        + response.content.decode(response.charset)
                    )
