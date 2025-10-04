"""
Class-modifying mixins that need to be standalone to avoid circular imports.
"""

from django.urls import NoReverseMatch, reverse

from nautobot.core.utils.lookup import get_route_for_model


class DataComplianceMixin:
    """
    Adds a `get_data_compliance_url` that can be applied to instances.
    """

    is_data_compliance_model = True

    def get_data_compliance_url(self, api=False):
        """Return the data compliance URL for a given instance."""
        # If is_data_compliance_model overridden should allow to opt out
        if not self.is_data_compliance_model:
            return None
        route = get_route_for_model(self, "data-compliance", api=api)

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]
        for field in fields:
            if not hasattr(self, field):
                continue

            try:
                return reverse(route, kwargs={field: getattr(self, field)})
            except NoReverseMatch:
                continue

        return None
