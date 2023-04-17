from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer

from nautobot.core.celery import NautobotKombuJSONEncoder


class FormlessBrowsableAPIRenderer(BrowsableAPIRenderer):
    """
    Override the built-in BrowsableAPIRenderer to disable HTML forms.
    """

    def show_form_for_method(self, *args, **kwargs):
        return False

    def get_filter_form(self, data, view, request):
        return None


class NautobotJSONRenderer(JSONRenderer):
    encoder_class = NautobotKombuJSONEncoder
