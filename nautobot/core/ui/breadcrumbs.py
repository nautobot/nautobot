from django.template import Context


class Breadcrumbs:

    def __init__(self):
        pass

    def get_extra_context(self, context: Context):
        """
        Provide additional data to include in the rendering context, based on the configuration of this component.

        Returns:
            (dict): Additional context data.
        """
        return {}
