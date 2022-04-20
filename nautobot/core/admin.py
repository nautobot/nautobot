from django.contrib.admin import site as admin_site, ModelAdmin
from django.db import models

from constance.admin import ConstanceAdmin, ConstanceForm, Config
from django_celery_beat import admin  # noqa: F401
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from social_django.models import Association, Nonce, UserSocialAuth
from taggit.models import Tag

from nautobot.utilities.forms import BootstrapMixin
import nautobot.utilities.forms.widgets as widgets


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


# Customize Constance admin
class ConfigForm(BootstrapMixin, ConstanceForm):
    """Apply Bootstrap styling to ConstanceForm."""


class ConfigAdmin(ConstanceAdmin):
    change_list_form = ConfigForm
    change_list_template = "admin/config/config.html"


admin_site.unregister([Config])
admin_site.register([Config], ConfigAdmin)


class NautobotModelAdmin(ModelAdmin):
    formfield_overrides = {
        models.DateField: {"widget": widgets.DatePicker},
        models.ForeignKey: {"widget": widgets.StaticSelect2},
        models.ManyToManyField: {"widget": widgets.StaticSelect2Multiple},
    }
