from django.template import Context
from django.template.loader import render_to_string
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from nautobot.core.templatetags import helpers
from nautobot.core.ui.object_detail import Button, KeyValueTablePanel, ObjectFieldsPanel
from nautobot.core.views.utils import get_obj_from_context


class JobRunScheduleButton(Button):
    """
    A custom button for running or scheduling a job.

    This button is rendered only if the user has the 'extras.run_job' permission.
    It also disables itself (via HTML 'disabled' attribute) if the related object is not
    installed or not enabled.
    """

    def get_extra_context(self, context):
        """Inject dynamic attributes (e.g. 'disabled') based on object state into the rendering context."""
        extra_context = super().get_extra_context(context)
        obj = context.get("object")
        if not obj.installed or not obj.enabled:
            if extra_context["attributes"] is None:
                extra_context["attributes"] = {}
            extra_context["attributes"]["disabled"] = "disabled"
        return extra_context


class JobKeyValueOverrideValueTablePanel(KeyValueTablePanel):
    """A table panel for displaying key-value pairs of job-related attributes, along with any override values defined on the job object."""

    def _render_overridden_text(self, text):
        """
        Render a simple overridden value inside a muted <span>, with a customizable prefix.

        Args:
            value (str): The content to display.
            prefix (str): The label shown before the value (default: 'default is').
        """
        return format_html('<span class="text-muted">overridden; default is {}</span>', mark_safe(text))  # noqa: S308

    def _render_overridden_block(self, content):
        """
        Render a more complex block of HTML content (like rendered markdown or JSON)
        in a div with a muted label indicating it's an overridden value.
        """
        return format_html('<div class="text-muted">overridden; default is:<br>{}</div>', content)

    def render_description_default(self, default_value):
        """
        Render a description field's default value as markdown.

        If the default value is a string, it is rendered as markdown;
        otherwise, a placeholder is shown.
        """
        rendered = (
            helpers.render_markdown(default_value)
            if isinstance(default_value, str)
            else helpers.placeholder(default_value)
        )
        return self._render_overridden_block(rendered)

    def render_time_limit_default(self, default_value, system_default_value, override=True):
        """
        Render a time limit value, falling back to the system default if needed.
        """
        message = "{} seconds" if default_value > 0 else "{} seconds (system default)"
        value = default_value if default_value > 0 else system_default_value
        if not override:
            return message.format(value)
        return self._render_overridden_text(message.format(value))

    def render_job_queues_default(self, obj):
        """
        Render the job's default task queues as JSON.

        Attempts to retrieve the `task_queues` from the job's class and render
        it using a JSON template. Falls back to a placeholder on error.
        """
        try:
            data = obj.job_class.task_queues
            rendered = render_to_string("extras/inc/json_data.html", {"data": data, "format": "json"})
        except Exception:
            rendered = helpers.placeholder(None)
        return self._render_overridden_block(rendered)

    def render_default_job_queue_default(self, obj):
        """
        Render the default job queue name from the job class.

        Retrieves the first queue from `task_queues` if available.
        Falls back to a placeholder if no queues are present.
        """
        try:
            queue = obj.job_class.task_queues[0]
        except (AttributeError, IndexError, TypeError):
            queue = helpers.placeholder("not specified")
        return self._render_overridden_text(queue)

    def render_boolean_default(self, default_value):
        """Render a boolean default value using a standardized visual format."""
        return self._render_overridden_text(helpers.render_boolean(default_value))

    def render_override_value(self, key, obj):
        """Render the override value for a given key on a job object."""
        override_attr = f"{key}_override"

        if not getattr(obj, override_attr, None):
            return ""

        if not obj.installed:
            return self._render_overridden_text("default is unknown (not currently installed)")

        try:
            default_value = getattr(obj.job_class, key)
        except Exception:
            default_value = "unknown"

        renderers = {
            "description": self.render_description_default,
            "soft_time_limit": lambda v: self.render_time_limit_default(
                v, helpers.settings_or_config("CELERY_TASK_SOFT_TIME_LIMIT")
            ),
            "time_limit": lambda v: self.render_time_limit_default(
                v, helpers.settings_or_config("CELERY_TASK_TIME_LIMIT")
            ),
            "job_queues": lambda _: self.render_job_queues_default(obj),
            "default_job_queue": lambda _: self.render_default_job_queue_default(obj),
        }

        if key in renderers:
            return renderers[key](default_value)

        if isinstance(default_value, bool):
            return self.render_boolean_default(default_value)

        return self._render_overridden_text(f'"{default_value}"')

    def render_job_queues_list(self, value):
        """Renders a <ul> HTML list of job queues with hyperlinks, or a placeholder if none exist."""
        if not value or not value.exists():
            return helpers.placeholder(None)

        items = format_html_join("\n", "<li>{}</li>", ((helpers.hyperlinked_object(q),) for q in value.all()))
        return format_html("<ul>{}</ul>", items)

    def render_body_content(self, context: Context):
        """Render the body content of the panel as a table of key-value rows, including any override information."""
        data = self.get_data(context)
        obj = get_obj_from_context(context)

        if not data:
            return format_html('<tr><td colspan="2">{}</td></tr>', helpers.placeholder(data))

        result = format_html("")
        panel_label = helpers.slugify(self.label or "")
        for key, value in data.items():
            key_display = self.render_key(key, value, context)
            override_value_display = self.render_override_value(key, obj)
            if value_display := self.render_value(key, value, context):
                if value_display is helpers.HTML_NONE:
                    value_tag = value_display
                else:
                    value_tag = format_html(
                        """
                            <span class="hover_copy">
                                <span id="{unique_id}_value_{key}">{value}</span>
                                <button class="btn btn-inline btn-default hover_copy_button" data-clipboard-target="#{unique_id}_value_{key}">
                                    <span class="mdi mdi-content-copy"></span>
                                </button>
                            </span>
                        """,
                        # key might not be globally unique in a page, but is unique to a panel;
                        # Hence we add the panel label to make it globally unique to the page
                        unique_id=panel_label,
                        key=helpers.slugify(key),
                        value=value_display,
                    )
                result += format_html(
                    "<tr><td>{}</td><td>{}</td><td>{}</td></tr>",
                    key_display,
                    value_tag,
                    override_value_display,
                )

        return result


class JobObjectFieldsPanel(ObjectFieldsPanel, JobKeyValueOverrideValueTablePanel):
    """
    ObjectFieldsPanel that renders its fields in a 3-column layout.
    Inherits behavior from ObjectFieldsPanel but overrides rendering with JobKeyValueOverrideValueTablePanel.
    """

    def render_value(self, key, value, context: Context):
        if key == "job_queues":
            return self.render_job_queues_list(value)
        if key == "soft_time_limit":
            value = self.render_time_limit_default(
                value, helpers.settings_or_config("CELERY_TASK_SOFT_TIME_LIMIT"), override=False
            )
        if key == "time_limit":
            value = self.render_time_limit_default(
                value, helpers.settings_or_config("CELERY_TASK_TIME_LIMIT"), override=False
            )
        return super().render_value(key, value, context)
