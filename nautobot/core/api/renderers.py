from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.renderers import JSONRenderer
from rest_framework.utils.encoders import JSONEncoder
from taggit.managers import _TaggableManager

from nautobot.core.models.generics import _NautobotTaggableManager
from nautobot.core.utils.requests import NautobotFakeRequest


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
        if isinstance(obj, (_NautobotTaggableManager, _TaggableManager)):
            obj = list(obj.values_list("id", flat=True))
        if isinstance(obj, NautobotFakeRequest):
            obj = obj.nautobot_serialize()
        return super().default(obj)


class NautobotJSONRenderer(JSONRenderer):
    encoder_class = NautobotJSONEncoder
