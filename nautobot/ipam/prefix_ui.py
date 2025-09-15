import logging

from django.template import Context
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html

from nautobot.core.templatetags import helpers
from nautobot.core.ui.object_detail import (
    Button,
    DistinctViewTab,
    KeyValueTablePanel,
    ObjectFieldsPanel,
    ObjectsTablePanel,
)
from nautobot.core.views.utils import get_obj_from_context

logger = logging.getLogger(__name__)


class IPAddressDistinctViewTab(DistinctViewTab):
    def render_label(self, context):
        obj = get_obj_from_context(context)
        get_all_ips = getattr(obj, "get_all_ips", None)
        if not callable(get_all_ips):
            return super().render_label(context)

        try:
            count = get_all_ips().count()
        except Exception as e:
            logger.warning(f"Could not count IPs for {obj}: {e}")
            return super().render_label(context)

        count = get_all_ips().count()
        if count is None:
            return super().render_label(context)

        return format_html(
            "{} {}",
            self.label,
            render_to_string("utilities/templatetags/badge.html", helpers.badge(count, True)),
        )


class PrefixChildTablePanel(ObjectsTablePanel):
    def should_render(self, context: Context):
        if not super().should_render(context):
            return False
        return context.get("active_tab") == "prefixes"


class IPAddressTablePanel(ObjectsTablePanel):
    def should_render(self, context: Context):
        if not super().should_render(context):
            return False
        return context.get("active_tab") == "ip-addresses"


class AddChildPrefixButton(Button):
    """Custom button to add a child prefix inside a Prefix detail view."""

    def should_render(self, context: Context):
        if not super().should_render(context):
            return False
        return context.get("active_tab") == "prefixes" and context.get("first_available_prefix") is not None

    def get_link(self, context):
        from urllib.parse import urlencode

        obj = get_obj_from_context(context)
        first_available_prefix = context.get("first_available_prefix")
        if not first_available_prefix:
            return None

        params = {
            "prefix": str(first_available_prefix),
            "namespace": getattr(obj.namespace, "pk", None),
            "tenant_group": getattr(getattr(obj.tenant, "tenant_group", None), "pk", None),
            "tenant": getattr(obj.tenant, "pk", None),
        }
        if obj.locations.exists():
            params["locations"] = [loc.pk for loc in obj.locations.all()]

        return f"{reverse(self.link_name)}?{urlencode(params)}"


class AddIPAddressButton(Button):
    """Custom button to add an IP address inside a Prefix detail view."""

    def should_render(self, context: Context):
        if not super().should_render(context):
            return False
        return context.get("active_tab") == "ip-addresses" and context.get("first_available_ip") is not None

    def get_link(self, context: Context):
        from urllib.parse import urlencode

        obj = get_obj_from_context(context)
        first_available_ip = context.get("first_available_ip")
        if not first_available_ip:
            return None

        params = {
            "address": first_available_ip,
            "namespace": getattr(obj.namespace, "pk", None),
            "tenant_group": getattr(getattr(obj.tenant, "tenant_group", None), "pk", None),
            "tenant": getattr(obj.tenant, "pk", None),
        }
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
    ObjectFieldsPanel that renders its fields in a 3-column layout.
    Inherits behavior from ObjectFieldsPanel but overrides rendering with PrefixKeyValueOverrideValueTablePanel.
    """

    def get_data(self, context):
        data = super().get_data(context)
        fields = self.fields
        instance = get_obj_from_context(context, self.context_object_key)

        if instance and "utilization" in fields:
            try:
                data["utilization"] = instance.get_utilization()
            except Exception:
                data["utilization"] = None

        return data

    def render_value(self, key, value, context):
        instance = get_obj_from_context(context)
        if key == "utilization":
            return self.render_utilization(value)
        if key == "locations":
            return self.render_locations_list(key, value, instance)

        return super().render_value(key, value, context)
