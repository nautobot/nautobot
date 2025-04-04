from django.utils.functional import classproperty
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.compat import unicode_http_header
from rest_framework.settings import api_settings
from rest_framework.utils.mediatypes import _MediaType
from rest_framework.versioning import AcceptHeaderVersioning


class APIVersionMismatch(exceptions.APIException):
    status_code = 400
    default_detail = _('Version mismatch between "Accept" header and query parameter.')


class NautobotAPIVersioning(AcceptHeaderVersioning):
    """Support both accept-header versioning and query-parameter versioning as options."""

    header_version_param = "version"  # staying consistent with pre-1.3 versions of Nautobot
    query_version_param = "api_version"  # to avoid ambiguity with filtersets potentially including a "version" param

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def allowed_versions(cls):  # pylint: disable=no-self-argument
        """
        List of version strings that are accepted by this class, based on api_settings.ALLOWED_VERSIONS.

        The base `AcceptHeaderVersioning.allowed_versions` is a class property that is set at import time,
        which means that things like `@override_settings` in tests happen "too late" to change it.
        By re-implementing it as a property, we bypass that problem.
        """
        return api_settings.ALLOWED_VERSIONS

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def default_version(cls):  # pylint: disable=no-self-argument
        """
        Default version number to use if unspecified by the requester, based on api_settings.DEFAULT_VERSION.

        The base `AcceptHeaderVersioning.default_version` is a class property that is set at import time,
        which means that things like `@override_settings` in tests happen "too late" to change it.
        By re-implementing it as a property, we bypass that problem.
        """
        return api_settings.DEFAULT_VERSION

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
            raise exceptions.NotAcceptable(
                f'Invalid version "{header_version}" in "Accept" header. Supported versions are: '
                + ", ".join(self.allowed_versions)
            )
        if query_version is not None and not self.is_allowed_version(query_version):
            # Behave like QueryParameterVersioning
            raise exceptions.NotFound(
                f'Invalid version "{query_version}" in query parameter. Supported versions are: '
                + ", ".join(self.allowed_versions)
            )
        version = header_version or query_version or self.default_version
        # self.default_version is always allowed, no need to re-check is_allowed_version here
        return version
