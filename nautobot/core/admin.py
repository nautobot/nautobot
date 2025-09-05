from constance.admin import Config, ConstanceAdmin, ConstanceForm
from django.contrib.admin import ModelAdmin, site as admin_site
from django.db import models
from django_celery_beat import admin  # noqa: F401  # unused-import -- but this import installs the beat admin
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
import social_django.admin  # noqa: F401  # unused-import -- but this import installs the social_django admin
from social_django.models import Association, Nonce, UserSocialAuth
import taggit.admin  # noqa: F401  # unused-import -- but this import installs the taggit admin
from taggit.models import Tag

from nautobot.core.forms import BootstrapMixin
import nautobot.core.forms.widgets as widgets

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
    """Extend Django's ModelAdmin to use some standard Nautobot UI widgets by default."""

    formfield_overrides = {
        models.DateField: {"widget": widgets.DatePicker},
        models.ForeignKey: {"widget": widgets.StaticSelect2},
        models.ManyToManyField: {"widget": widgets.StaticSelect2Multiple},
    }
