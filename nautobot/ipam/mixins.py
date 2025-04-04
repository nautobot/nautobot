class LocationToLocationsQuerySetMixin:
    """
    A mixin for Django QuerySets to support backward compatibility by converting
    queries from a previously used 'location' field to the new
    'locations'. This mixin intercepts `filter` and `exclude` calls
    to transform references from 'location' to 'locations'.
    """

    def _convert_location_to_locations(self, kwargs):
        """Transforms query parameters that reference 'location' field into the corresponding 'locations' field."""
        updated_kwargs = {}
        for field, value in kwargs.items():
            if field == "location":
                # If there is no lookup expression, it means 'location' is queried directly,
                # thus use 'locations__in' to accommodate the ManyToMany relationship
                updated_kwargs["locations__in"] = [value]
            elif field.startswith("location__"):
                # If there is a lookup expression following 'location', prepend it with 'locations'
                _, lookup_expr = field.split("location", maxsplit=1)
                locations_field = f"locations{lookup_expr}".strip()
                updated_kwargs[locations_field] = value
            else:
                updated_kwargs[field] = value
        return updated_kwargs

    def filter(self, *args, **kwargs):
        kwargs = self._convert_location_to_locations(kwargs)
        return super().filter(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        kwargs = self._convert_location_to_locations(kwargs)
        return super().exclude(*args, **kwargs)
