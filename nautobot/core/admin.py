from django.contrib.admin import site as admin_site
from social_django.models import Association, Nonce, UserSocialAuth
from taggit.models import Tag
from django.db import models
from django_celery_beat.admin import ClockedScheduleAdmin as OverrideClockedScheduleAdmin
from django_celery_beat.models import ClockedSchedule
from nautobot.utilities.forms.widgets import DateTimePicker


class ClockedScheduleAdmin(OverrideClockedScheduleAdmin):
    formfield_overrides = {models.DateTimeField: {"widget": DateTimePicker}}


# Override default AdminSite attributes so we can avoid creating and
# registering our own class
admin_site.site_header = "Nautobot Administration"
admin_site.site_title = "Nautobot"

# Unregister the unused stock Tag model provided by django-taggit
admin_site.unregister(Tag)

# Re-register ClockedSchedule with custom widget
admin_site.unregister(ClockedSchedule)
admin_site.register(ClockedSchedule)

# Unregister SocialAuth from Django admin menu
admin_site.unregister(Association)
admin_site.unregister(Nonce)
admin_site.unregister(UserSocialAuth)
