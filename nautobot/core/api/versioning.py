from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.compat import unicode_http_header
from rest_framework.utils.mediatypes import _MediaType
from rest_framework.versioning import AcceptHeaderVersioning


class APIVersionMismatch(exceptions.APIException):
    status_code = 400
    default_detail = _('Version mismatch between "Accept" header and query parameter.')


class NautobotAPIVersioning(AcceptHeaderVersioning):
    """Support both accept-header versioning and query-parameter versioning as options."""

    invalid_version_in_header = _('Invalid version in "Accept" header. Supported versions are %(versions)s') % {
        "versions": ", ".join(settings.REST_FRAMEWORK["ALLOWED_VERSIONS"])
    }
    invalid_version_in_query = _("Invalid version in query parameter. Supported versions are %(versions)s") % {
        "versions": ", ".join(settings.REST_FRAMEWORK["ALLOWED_VERSIONS"])
    }

    header_version_param = "version"  # staying consistent with pre-1.3 versions of Nautobot
    query_version_param = "api_version"  # to avoid ambiguity with filtersets potentially including a "version" param

    def determine_version(self, request, *args, **kwargs):
        """Use either Accept header or query parameter for versioning."""

        # Patterned after rest_framework.versioning.AcceptHeaderVersioning
        media_type = _MediaType(request.accepted_media_type)
        header_version = media_type.params.get(self.header_version_param, None)
        if header_version is not None:
            header_version = unicode_http_header(header_version)

        # Patterned after rest_framework.versioning.QueryParameterVersioning
        query_version = request.query_params.get(self.query_version_param, None)

        if header_version is not None and query_version is not None and header_version != query_version:
            raise APIVersionMismatch()
        if header_version is not None and not self.is_allowed_version(header_version):
            # Behave like AcceptHeaderVersioning
            raise exceptions.NotAcceptable(self.invalid_version_in_header)
        if query_version is not None and not self.is_allowed_version(query_version):
            # Behave like QueryParameterVersioning
            raise exceptions.NotFound(self.invalid_version_in_query)
        version = header_version or query_version or self.default_version
        # self.default_version is always allowed, no need to re-check is_allowed_version here
        return version
