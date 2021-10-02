from django.conf import settings  # noqa: F401
from django.contrib.admin import site as admin_site
from social_django.models import Association, Nonce, UserSocialAuth
from taggit.models import Tag


# Override default AdminSite attributes so we can avoid creating and
# registering our own class
admin_site.site_header = "Nautobot Administration"
admin_site.site_title = "Nautobot"
admin_site.index_template = "admin/nautobot_index.html"

# Unregister the unused stock Tag model provided by django-taggit
admin_site.unregister(Tag)

# Unregister SocialAuth from Django admin menu
admin_site.unregister(Association)
admin_site.unregister(Nonce)
admin_site.unregister(UserSocialAuth)
