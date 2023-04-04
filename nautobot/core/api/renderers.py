from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.renderers import JSONRenderer
from rest_framework.utils.encoders import JSONEncoder

from nautobot.core.models.generics import _NautobotTaggableManager


class FormlessBrowsableAPIRenderer(BrowsableAPIRenderer):
    """
    Override the built-in BrowsableAPIRenderer to disable HTML forms.
    """

    def show_form_for_method(self, *args, **kwargs):
        return False

    def get_filter_form(self, data, view, request):
        return None


class NautobotJSONEncoder(JSONEncoder):
    """
    _NautobotTaggableManager is not JSON Serializable by default.
    So when depth=0, we have to intercept it here and make it render
    the tags UUIDs instead.
    """

    def default(self, obj):
        if isinstance(obj, _NautobotTaggableManager):
            obj = list(obj.values_list("id", flat=True))
        return super().default(obj)


class NautobotJSONRenderer(JSONRenderer):
    encoder_class = NautobotJSONEncoder
