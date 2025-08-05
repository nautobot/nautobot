from typing import Literal, Optional

from django.template import Context, Template
from django.utils.html import strip_tags

DEFAULT_TITLES: dict[str, str] = {
    "list": "{{ verbose_name_plural|bettertitle }}",
    "detail": "{{ object.display|default:object }}",
    "retrieve": "{{ object.display|default:object }}",
    "destroy": "Delete {{ verbose_name }}?",
    "create": "Add a new {{ verbose_name }}",
    "update": "Editing {{ verbose_name }} {{ object.display|default:object }}",
    "bulk_destroy": "Delete {{ total_objs_to_delete }} {{ verbose_name_plural|bettertitle }}?",
    "bulk_rename": "Renaming {{ selected_objects|length }} {{ verbose_name_plural|bettertitle }} on {{ parent_name }}",
    "bulk_update": "Editing {{ objs_count }} {{ verbose_name_plural|bettertitle }}",
    "changelog": "{{ object.display|default:object }} - Change Log",
    "notes": "{{ object.display|default:object }} - Notes",
    "approve": "Approve {{ verbose_name|bettertitle }}?",
    "deny": "Deny {{ verbose_name|bettertitle }}?",
}

DEFAULT_PLUGINS = ["helpers"]

ModeType = Literal["html", "plain"]


class Titles:
    """
    Base class for document titles and page headings.

    This class provides a mechanism to define per-action title templates.
    Titles can be dynamically rendered using context variables and template tags using the Django template engine and context.
    Use the `render()` method to obtain either rich (HTML) or plain (stripped of HTML) output.

    There is a dedicated simple tag to render `Titles` passed in the `context['view_titles']`: `{% render_title mode="html" %}`

    Attributes:
        titles (dict[str, str]): Action-to-title-template mapping.
        template_plugins (list[str]): List of Django template libraries to load before rendering.

    Args:
        template_plugins (Optional[list[str]]): Template libraries to load into rendering.
        titles (dict): Action-to-template-string mappings that override or extend the defaults.
    """

    def __init__(self, template_plugins: Optional[list[str]] = None, titles: Optional[dict[str, str]] = None):
        """
        Keyword arguments passed can either add new action-title pair or override existing titles.

        Args:
            template_plugins (Optional[list[str]]): Extra Django template libraries to load before rendering.
            titles (Optional[dict[str, str]]): Custom or overriding mappings from action to template string.
        """
        self.titles: dict[str, str] = DEFAULT_TITLES.copy()
        if titles:
            self.titles.update(**titles)

        self.template_plugins: list[str] = DEFAULT_PLUGINS.copy()
        if template_plugins:
            self.template_plugins.extend(template_plugins)

    def render(self, context: Context, mode: ModeType = "html") -> str:
        """
        Renders the title based on given context and current action.

        If mode == "plain", the output will be stripped of HTML tags.

        Make sure that needed context variables are in context and needed plugins are loaded.

        Args:
            context (Context): Render context.
            mode (ModeType): Rendering mode: "html" or "plain".

        Returns:
            (str): HTML fragment or plain text, depending on `mode`.
        """
        with context.update(self.get_extra_context(context)):
            template_str = self.get_template_str(context)
            template = Template(self.template_plugins_str + template_str)
            rendered_title = template.render(context)
            if mode == "plain":
                return strip_tags(rendered_title)
            return rendered_title

    def get_template_str(self, context: Context) -> str:
        """
        Determine the template string for the current action.

        Args:
            context (Context): Render context.

        Returns:
            str: The template string for the current action, or an empty string if not found.
        """
        action = context.get("view_action", "list")

        template_str = self.titles.get(action)
        if template_str:
            return template_str

        detail = context.get("detail", False)
        if detail:
            return self.titles.get("detail", "")

        return ""

    @property
    def template_plugins_str(self) -> str:
        """
        Return a concatenated string of Django {% load ... %} tags for all template plugins.

        Returns:
            str: String containing {% load ... %} tags for the required template libraries.
        """
        return "".join(f"{{% load {plugin_name} %}}" for plugin_name in self.template_plugins)

    def get_extra_context(self, context: Context) -> dict:
        """
        Provide additional data to include in the rendering context, based on the configuration of this component.

        Args:
            context (Context): The current template context.

        Returns:
            (dict): Additional context data.
        """
        return {}
