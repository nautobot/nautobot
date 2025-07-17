from typing import Optional

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


class Titles:
    """
    Base class for document titles and page headings.

    This class provides a mechanism to define per-action title templates.
    Titles can dynamically render using context variables and template tags.

    You can use this class directly or subclass it (e.g., `DocumentTitles`, `PageHeadings`)
    to customize rendering behavior (e.g., stripping HTML).

    Attributes:
        titles (dict[str, str]): Action-to-title-template mapping.
        template_plugins (list[str]): List of Django template libraries to load before rendering.

    Args:
        template_plugins (Optional[list[str]]): Template libraries to load into rendering.
        **kwargs (dict): Action-to-template-string mappings that override or extend the defaults.
    """

    def __init__(self, template_plugins: Optional[list[str]] = None, titles: Optional[dict[str, str]] = None):
        """
        Keyword arguments passed can either add new action-title pair or override existing titles.
        """
        self.titles: dict[str, str] = DEFAULT_TITLES.copy()
        if titles:
            self.titles.update(**titles)

        self.template_plugins: list[str] = DEFAULT_PLUGINS.copy()
        if template_plugins:
            self.template_plugins.extend(template_plugins)

    def render(self, context: Context) -> str:
        """
        Renders the title based on given context and current action.

        Make sure that needed context variables are in context and needed plugins are loaded.

        Returns:
            (str): HTML fragment.
        """
        with context.update(self.get_extra_context(context)):
            template_str = self.get_template_str(context)
            template = Template(self.template_plugins_str + template_str)
            return template.render(context)

    def get_template_str(self, context: Context) -> str:
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
        return "".join(f"{{% load {plugin_name} %}}" for plugin_name in self.template_plugins)

    def get_extra_context(self, context: Context) -> dict:
        """
        Provide additional data to include in the rendering context, based on the configuration of this component.

        Returns:
            (dict): Additional context data.
        """
        return {}


class DocumentTitles(Titles):
    """
    Class for titles being used as document title in browser. Makes sure that output will be stripped of any html tags.
    """

    def render(self, context: Context) -> str:
        rendered_template = super().render(context)
        return strip_tags(rendered_template)


class PageHeadings(Titles):
    """
    Class for titles being used as page heading.
    """

    def __init__(self, titles: Optional[dict[str, str]] = None, **kwargs):
        custom_titles = {"list": "{% format_title_with_saved_view verbose_name_plural|bettertitle %}"}
        if titles:
            custom_titles.update(titles)
        super().__init__(titles=custom_titles, **kwargs)
