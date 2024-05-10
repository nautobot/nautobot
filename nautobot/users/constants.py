import logging

from django.urls import NoReverseMatch, reverse

from nautobot.extras.utils import FeatureQuery

logger = logging.getLogger(__name__)

VIEW_NAMES = []
# Append all saved view supported view names
for choice in FeatureQuery("saved_views").get_choices():
    app_label, model = choice[0].split(".")
    # Relevant list view name only
    if app_label in ["circuits", "dcim", "ipam", "extras", "tenancy", "virtualization"]:
        list_view_name = f"{app_label}:{model}_list"
        try:
            reverse(list_view_name)
            VIEW_NAMES.append(f"{app_label}:{model}_list")
        except NoReverseMatch as e:
            logger.error(e)
