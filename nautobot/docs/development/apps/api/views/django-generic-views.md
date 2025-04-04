# Utilizing Generic Django Views

The use of `generic` Django views can aid in app development. As an example, let's write a view which displays a random animal and the sound it makes. First, create the view in `views.py`:

```python
# views.py
from django.shortcuts import render

from nautobot.apps.views import GenericView

from .models import Animal


class RandomAnimalView(GenericView):
    """Display a randomly-selected Animal."""

    def get(self, request):
        animal = Animal.objects.order_by('?').first()
        return render(request, 'nautobot_animal_sounds/animal.html', {
            'animal': animal,
        })
```

!!! tip
    The `nautobot.apps.views.GenericView` class was added in Nautobot 1.6.16 and 2.1.9. If you're developing against an earlier version, you can use `django.views.generic.View` in combination with the `django.contrib.auth.mixins.LoginRequiredMixin` instead.

This view retrieves a random animal from the database and and passes it as a context variable when rendering a template named `animal.html`, which doesn't exist yet. To create this template, first create a directory named `templates/nautobot_animal_sounds/` within the app source directory. (We use the app's name as a subdirectory to guard against naming collisions with other apps.) Then, create a template named `animal.html` as described below.
