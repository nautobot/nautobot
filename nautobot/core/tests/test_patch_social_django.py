"""
Test suite for social_django storage patch.

This tests that the monkeypatch correctly replaces the vulnerable create_user
method with the secure version that raises AuthAlreadyAssociated instead of
silently returning an existing user.

Please see nautobot/core/utils/patch_social_django.py for details on the patch.
"""

from unittest.mock import MagicMock, patch

from nautobot.core.testing import TestCase


class PatchSocialDjangoTestCase(TestCase):
    def test_django_storage_has_patch_at_import_time(self):
        """
        Test that importing DjangoStorage gives us the patched version.

        This verifies that the patch applied in CoreConfig.ready() persists
        and affects all imports of DjangoStorage throughout the application.
        """
        from django.db.utils import IntegrityError
        from social_core.exceptions import AuthAlreadyAssociated
        from social_django.models import DjangoStorage

        # Mock user model to trigger IntegrityError
        mock_user_model = MagicMock()
        mock_manager = MagicMock()
        mock_manager.create_user.side_effect = IntegrityError("duplicate key")
        mock_user_model._default_manager = mock_manager

        # Patch username_field and user_model methods to return our mock user model
        with patch.object(DjangoStorage.user, "username_field", return_value="username"):
            with patch.object(DjangoStorage.user, "user_model", return_value=mock_user_model):
                # Should raise AuthAlreadyAssociated (patched behavior)
                with self.assertRaises(AuthAlreadyAssociated):
                    DjangoStorage.user.create_user(username="test", email="test@example.com")

                # Verify vulnerable get() not called
                mock_manager.get.assert_not_called()
