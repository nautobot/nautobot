from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.versioning import AcceptHeaderVersioning


class NautobotAcceptHeaderVersioning(AcceptHeaderVersioning):
    """Extend the DRF AcceptHeaderVersioning class with a more verbose rejection message."""

    invalid_version_message = _('Invalid version in "Accept" header. Supported versions are %(versions)s') % {
        "versions": ", ".join(settings.REST_FRAMEWORK["ALLOWED_VERSIONS"])
    }
