from nautobot.extras.plugins import TemplateExtension
from django.urls import reverse

class ValidationTab(TemplateExtension):
    def detail_tabs(self):
        return [
            {
                "title": "Validations",
                "url": reverse(self.reverse_url, kwargs={"id": self.context["object"].id})
            }
        ]
