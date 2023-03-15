from django.db.models import Manager


class BaseManager(Manager):
    """
    Base manager class corresponding to BaseModel and RestrictedQuerySet.

    Adds built-in natural key support, loosely based on `django-natural-keys`.
    """

    def get_by_natural_key(self, *args):
        """
        Return the object corresponding to the provided natural key.

        Generic implementation that depends on the model being a BaseModel subclass or otherwise implementing our
        `natural_key_field_lookups` property API. Loosely based on implementation from `django-natural-keys`.
        """
        base_kwargs = self.model.natural_key_args_to_kwargs(args)

        # Since base_kwargs already has __ lookups in it, we could just do "return self.get(**base_kwargs)"
        # But we'll inherit a pattern from django-natural-keys where we replace nested related field lookups with
        # calls to `related_model.objects.get_by_natural_key()` just in case it has a custom/overridden implementation.
        nested_lookups = {}
        kwargs = {}
        for field_lookup in self.model.natural_key_field_lookups:
            if "__" in field_lookup:
                field_name, _ = field_lookup.split("__", 1)
                nested_lookups.setdefault(field_name, []).append(base_kwargs[field_lookup])
            else:
                kwargs[field_lookup] = base_kwargs[field_lookup]

        # Look up the related model instances by their own natural keys.
        # If any related lookup fails, then the base model lookup can automatically fail as a result.
        for field_name, related_values in nested_lookups.items():
            # Handle the case where the related lookup is actually looking for a null reference.
            if all(related_value is None for related_value in related_values):
                kwargs[f"{field_name}__isnull"] = True
                continue
            related_model = self.model._meta.get_field(field_name).remote_field.model
            try:
                kwargs[field_name] = related_model.objects.get_by_natural_key(*related_values)
            except related_model.DoesNotExist as exc:
                raise self.model.DoesNotExist() from exc

        return self.get(**kwargs)
