from django.contrib.admin import site as admin_site
from social_django.models import Association, Nonce, UserSocialAuth
from taggit.models import Tag
from django_celery_beat import admin  # noqa: F401
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)


# Override default AdminSite attributes so we can avoid creating and
# registering our own class
admin_site.site_header = "Nautobot Administration"
admin_site.site_title = "Nautobot"

# Unregister the unused stock Tag model provided by django-taggit
admin_site.unregister(Tag)

# Remove Celery Beat from admin menu
admin_site.unregister(ClockedSchedule)
admin_site.unregister(CrontabSchedule)
admin_site.unregister(IntervalSchedule)
admin_site.unregister(PeriodicTask)
admin_site.unregister(SolarSchedule)

# Unregister SocialAuth from Django admin menu
admin_site.unregister(Association)
admin_site.unregister(Nonce)
admin_site.unregister(UserSocialAuth)
