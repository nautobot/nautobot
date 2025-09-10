import logging

from django.template import Context
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from nautobot.core.templatetags import helpers
from nautobot.core.ui.object_detail import Button, DistinctViewTab, KeyValueTablePanel, ObjectFieldsPanel
from nautobot.core.views.utils import get_obj_from_context

logger = logging.getLogger(__name__)


class ChildPrefixDistinctViewTab(DistinctViewTab):
    def render_label(self, context):
        obj = get_obj_from_context(context)
        count = getattr(obj, "descendants_count", None)
        if count is None:
            return super().render_label(context)

        return format_html(
            "{} {}",
            self.label,
            render_to_string("utilities/templatetags/badge.html", helpers.badge(count, True)),
        )


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


class ToggleAvailableButton(Button):
    """Button for toggling show/hide available prefixes."""

    def __init__(self, show: bool, **kwargs):
        label = "Show available" if show else "Hide available"
        icon = "mdi-eye-outline" if show else "mdi-eye-off-outline"
        super().__init__(label=label, icon=icon, **kwargs)
        self.show = show

    def should_render(self, context: Context):
        if not super().should_render(context):
            return False
        return context.get("show_available", False)

    def get_link(self, context):
        request = context["request"]
        return f"{request.path}{helpers.legacy_querystring(request, show_available=str(self.show).lower())}"

    def get_extra_context(self, context):
        ctx = super().get_extra_context(context)
        show_available = context.get("show_available")
        is_active = (show_available is True and self.show) or (show_available is False and not self.show)

        # merge classes (do not overwrite the whole attributes dict)
        attrs = dict(ctx.get("attributes") or {})
        existing_classes = (attrs.get("class") or "").strip()
        extra = "active disabled" if is_active else ""
        combined = " ".join(filter(None, [existing_classes, extra]))
        if combined:
            attrs["class"] = combined
        else:
            # ensure 'class' key exists only when needed (template prepends 'btn btn-default' anyway)
            attrs.pop("class", None)

        ctx["attributes"] = attrs
        return ctx


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
            "prefix": first_available_prefix,
            "namespace": getattr(obj.namespace, "pk", None),
            "tenant_group": getattr(getattr(obj.tenant, "tenant_group", None), "pk", None),
            "tenant": getattr(obj.tenant, "pk", None),
        }
        if obj.locations.exists():
            params["locations"] = [loc.pk for loc in obj.locations.all()]

        return f"{reverse(self.link_name)}?{urlencode(params, doseq=True)}"


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


class PrefixObjectFieldsPanel(ObjectFieldsPanel):  # , PrefixKeyValueOverrideValueTablePanel):
    """
    ObjectFieldsPanel that renders its fields in a 3-column layout.
    Inherits behavior from ObjectFieldsPanel but overrides rendering with JobKeyValueOverrideValueTablePanel.
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

    def render_locations_list(self, value):
        """Renders a <ul> HTML list of job queues with hyperlinks, or a placeholder if none exist."""
        if not value or not value.exists():
            return helpers.placeholder(None)

        items = format_html_join("\n", "<li>{}</li>", ((helpers.hyperlinked_object(q),) for q in value.all()))
        return format_html("<ul>{}</ul>", items)

    def render_value(self, key, value, context):
        if key == "ip_version":
            return f"IPv{value}"
        if key == "utilization":
            if value is None:
                return helpers.placeholder(None)
            return render_to_string(
                "utilities/templatetags/utilization_graph.html",
                helpers.utilization_graph(value),
            )
        if key == "locations":
            return self.render_locations_list(value)

        return super().render_value(key, value, context)
