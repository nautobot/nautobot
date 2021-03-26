from django.conf import settings
from django.contrib.admin import site as admin_site
from taggit.models import Tag


# Override default AdminSite attributes so we can avoid creating and
# registering our own class
admin_site.site_header = "Nautobot Administration"
admin_site.site_title = "Nautobot"
admin_site.index_template = "admin/nautobot_index.html"

# Unregister the unused stock Tag model provided by django-taggit
admin_site.unregister(Tag)
