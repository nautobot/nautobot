from django.test import tag

from nautobot.core.testing import TestCase
from nautobot.core.utils.lookup import get_url_for_url_pattern, get_url_patterns


@tag("integration")
class AuthenticationEnforcedTestCase(TestCase):
    r"""
    Test that all\* registered views require authentication to access.

    \* with a very small number of known exceptions such as login and logout views.
    """

    def test_all_views_require_authentication(self):
        self.client.logout()
        url_patterns = get_url_patterns(ignore_redirects=True)

        for url_pattern in url_patterns:
            with self.subTest(url_pattern=url_pattern):
                url = get_url_for_url_pattern(url_pattern)
                response = self.client.get(url, follow=True)

                if response.status_code == 405:  # Method not allowed
                    response = self.client.post(url, follow=True)

                # Is a view that *should* be open to unauthenticated users?
                if url in [
                    "/admin/login/",
                    "/api/plugins/example-app/webhook/",
                    "/health/",
                    "/login/",
                    "/media-failure/",
                    "/robots.txt",
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
                elif response.status_code != 403:
                    if any(
                        url.startswith(path)
                        for path in [
                            "/complete/",  # social auth
                            "/health/string/",  # health-check
                            "/login/",  # social auth
                            "/media/",  # MEDIA_ROOT
                            "/plugins/example-app/docs/",  # STATIC_ROOT
                        ]
                    ):
                        self.assertEqual(response.status_code, 404)
                    else:
                        self.fail(
                            f"Unexpected {response.status_code} response at {url}: "
                            + response.content.decode(response.charset)
                        )
