import logging
from urllib.parse import urlencode

from django.template import Context
from django.template.loader import render_to_string
from django.urls import reverse

from nautobot.core.templatetags import helpers
from nautobot.core.ui.object_detail import (
    Button,
    KeyValueTablePanel,
    ObjectFieldsPanel,
)
from nautobot.core.views.utils import get_obj_from_context

logger = logging.getLogger(__name__)


class AddChildPrefixButton(Button):
    """Custom button to add a child prefix inside a Prefix detail view."""

    def should_render(self, context: Context):
        if not super().should_render(context):
            return False
        return context.get("first_available_prefix") is not None

    def get_link(self, context):
        first_available_prefix = context.get("first_available_prefix")
        obj = get_obj_from_context(context)
        if not first_available_prefix:
            return None

        params = {
            "prefix": str(first_available_prefix),
            "namespace": obj.namespace.pk,
        }
        if obj.tenant:
            params["tenant"] = obj.tenant.pk
            if obj.tenant.tenant_group:
                params["tenant_group"] = obj.tenant.tenant_group.pk
        if obj.locations.exists():
            params["locations"] = [loc.pk for loc in obj.locations.all()]

        return f"{reverse(self.link_name)}?{urlencode(params)}"


class AddIPAddressButton(Button):
    """Custom button to add an IP address inside a Prefix detail view."""

    def should_render(self, context: Context):
        if not super().should_render(context):
            return False
        return context.get("first_available_ip") is not None

    def get_link(self, context: Context):
        first_available_ip = context.get("first_available_ip")
        obj = get_obj_from_context(context)
        if not first_available_ip:
            return None

        params = {
            "address": first_available_ip,
            "namespace": obj.namespace.pk,
        }
        if obj.tenant:
            params["tenant"] = obj.tenant.pk
            if obj.tenant.tenant_group:
                params["tenant_group"] = obj.tenant.tenant_group.pk
        return f"{reverse(self.link_name)}?{urlencode(params)}"


class PrefixKeyValueOverrideValueTablePanel(KeyValueTablePanel):
    """A table panel for displaying key-value pairs of prefix-related attributes, along with any override values defined on the prefix object."""

    def render_locations_list(self, key, value, instance):
        """Renders a <ul> HTML list of locations with hyperlinks, or a placeholder if none exist."""
        if not value or not value.exists():
            return helpers.placeholder(None)

        base_url = reverse("dcim:location_list")
        full_listing_link = f"{base_url}?prefixes={instance.pk}"

        return helpers.render_m2m(
            value.all(),
            full_listing_link=full_listing_link,
            verbose_name_plural=key,
        )

    def render_utilization(self, value):
        """Renders a utilization graph, or a placeholder if none exist."""
        if value is None:
            return helpers.placeholder(None)
        return render_to_string(
            "utilities/templatetags/utilization_graph.html",
            helpers.utilization_graph(value),
        )


class PrefixObjectFieldsPanel(ObjectFieldsPanel, PrefixKeyValueOverrideValueTablePanel):
    """
    A panel that combines field rendering from ObjectFieldsPanel with the
    key/value rendering style of PrefixKeyValueOverrideValueTablePanel.

    - Adds custom handling for specific fields such as:
      - "utilization": retrieved from the instance via get_utilization().
      - "locations": rendered as a locations list.
    Falls back to the parent class rendering for all other fields.
    """

    def get_data(self, context):
        data = super().get_data(context)
        fields = self.fields
        instance = get_obj_from_context(context, self.context_object_key)

        if instance and "utilization" in fields:
            data["utilization"] = instance.get_utilization()

        return data

    # TODO: can be removed as a part of NAUTOBOT-1052
    def render_value(self, key, value, context):
        instance = get_obj_from_context(context)
        if key == "utilization":
            return self.render_utilization(value)
        if key == "locations":
            return self.render_locations_list(key, value, instance)

        return super().render_value(key, value, context)
