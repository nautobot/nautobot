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


class Titles:
    """
    Base class for document titles and page headings.
    """



    default_plugins = "{% load helpers %}"

    def __init__(self, additional_template_plugins=None, **kwargs):
        """
        Keyword arguments passed can either add new action-title pair or override existing titles.
        """
        self.titles = DEFAULT_TITLES.copy()
        self.titles.update(kwargs)

        self.additional_template_plugins = additional_template_plugins or self.default_plugins

    def render(self, context: Context):
        """
        Renders the title based on given context and current action.

        Make sure that needed context variables are in context and needed plugins are loaded.

        Returns:
            (str): HTML fragment.
        """
        with context.update(self.get_extra_context(context)):
            action = context.get("view_action", "list_action")
            template_str = self.titles.get(f"{action}_action", "")
            template = Template(self.additional_template_plugins + template_str)
            return template.render(context)

    def get_extra_context(self, context: Context):
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

    def render(self, context: Context):
        rendered_template = super().render(context)
        return strip_tags(rendered_template)


class PageHeadings(Titles):
    """
    Class for titles being used as page heading.
    """

    def __init__(self, list_action=None, **kwargs):
        default_list_action = "{% format_title_with_saved_view obj_type_plural|bettertitle %}"
        super().__init__(list_action=(list_action or default_list_action), **kwargs)
