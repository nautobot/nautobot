"""Template content for nautobot_data_validation_engine."""

from django.urls import reverse
from nautobot.extras.plugins import TemplateExtension
from nautobot.extras.utils import registry


def tab_factory(content_type_label):
    """Generate a DataComplianceTab object for a given content type."""

    class DataComplianceTab(TemplateExtension):  # pylint: disable=W0223
        """Dynamically generated DataComplianceTab class."""

        model = content_type_label

        def detail_tabs(self):
            return [
                {
                    "title": "Data Compliance",
                    "url": reverse(
                        "plugins:nautobot_data_validation_engine:data-compliance-tab",
                        kwargs={"id": self.context["object"].id, "model": self.model},
                    ),
                },
            ]

    return DataComplianceTab


class ComplianceTemplateIterator:
    """Iterator that generates PluginCustomValidator classes for each model registered in the extras feature query registry 'custom_validators'."""

    def __iter__(self):
        """Return a generator of PluginCustomValidator classes for each registered model."""
        for app_label, models in registry["model_features"]["custom_validators"].items():
            for model in models:
                label = f"{app_label}.{model}"
                yield tab_factory(label)


template_extensions = ComplianceTemplateIterator()
