from rest_framework import renderers


class NautobotHTMLRender(renderers.BrowsableAPIRenderer):
    template = None
    default_return_url = None

    def get_context(self, data, accepted_media_type, renderer_context):
        context = super().get_context(data, accepted_media_type, renderer_context)
        context.update(data)
        return context

    def render(self, data, accepted_media_type=None, renderer_context=None):
        self.template = data["template"]
        return super().render(data, accepted_media_type=accepted_media_type, renderer_context=renderer_context)
