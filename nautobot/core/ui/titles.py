from typing import Optional

from django.template import Context, Template
from django.utils.html import strip_tags

DEFAULT_TITLES: [str, str] = {
    "list_action": "{{ obj_type_plural|bettertitle }}",
    "retrieve_action": "{{ object.display|default:object }}",
    "destroy_action": "Delete {{ obj_type }}?",
    "create_action": "Add a new {{ obj_type }}",
    "update_action": "Editing {{ obj_type }} {{ obj }}",
    "bulk_destroy_action": "Delete {{ total_objs_to_delete }} {{ obj_type_plural|bettertitle }}?",
    "bulk_rename_action": "Renaming {{ selected_objects|length }} {{ obj_type_plural|bettertitle }} on {{ parent_name }}",
    "bulk_update_action": "Editing {{ objs_count }} {{ obj_type_plural|bettertitle }}",
    "changelog_action": "{{ object.display|default:object }} - Change Log",
    "notes_action": "{{ object.display|default:object }} - Notes",
    "approve_action": "Approve {{ obj_type }}?",
    "deny_action": "Deny {{ obj_type }}?",
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

    def __init__(self, template_plugins: Optional[list[str]] = None, **kwargs):
        """
        Keyword arguments passed can either add new action-title pair or override existing titles.
        """
        self.titles: dict[str, str] = DEFAULT_TITLES.copy()
        self.titles.update(kwargs)

        self.template_plugins: list[str] = template_plugins or DEFAULT_PLUGINS

    def render(self, context: Context) -> str:
        """
        Renders the title based on given context and current action.

        Make sure that needed context variables are in context and needed plugins are loaded.

        Returns:
            (str): HTML fragment.
        """
        with context.update(self.get_extra_context(context)):
            action = context.get("view_action", "list_action")
            template_str = self.titles.get(f"{action}_action", "")
            template = Template(self.template_plugins_str + template_str)
            return template.render(context)

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

    def __init__(self, list_action=None, **kwargs):
        default_list_action = "{% format_title_with_saved_view obj_type_plural|bettertitle %}"
        super().__init__(list_action=(list_action or default_list_action), **kwargs)
