# Using the Django Admin Interface

Apps can optionally expose their models via Django's built-in [administrative interface](https://docs.djangoproject.com/en/stable/ref/contrib/admin/). This can greatly improve troubleshooting ability, particularly during development. To expose a model, simply register it using Django's `admin.register()` function. An example `admin.py` file for the above model is shown below:

```python
# admin.py
from django.contrib import admin
from nautobot.apps.admin import NautobotModelAdmin

from .models import Animal


@admin.register(Animal)
class AnimalAdmin(NautobotModelAdmin):
    list_display = ('name', 'sound')
```

This will display the app and its model in the admin UI. Staff users can create, change, and delete model instances via the admin UI without needing to create a custom view.

![Nautobot app in the admin UI](../../../../media/plugins/plugin_admin_ui.png)
