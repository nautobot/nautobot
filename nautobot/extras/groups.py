import inspect
from collections import OrderedDict


class BaseDynamicGroupMap:

    model = None
    filterset = None

    field_order = []
    field_exclude = ["model", "filterset", "field_order", "field_exclude"]

    @classmethod
    def _get_field_names(cls):
        """Return a list of the name of all fields."""
        _field_names = []
        for attr in dir(cls):

            if attr in cls.field_exclude or attr.startswith("__") or attr.startswith("_"):
                continue

            if not inspect.ismethod(getattr(cls, attr)):
                _field_names.append(attr)

        return sorted(_field_names)

    @classmethod
    def fields(cls):
        """Return all fields in a dictionnary."""
        _fields = OrderedDict()
        field_names = cls._get_field_names()
        
        # Remove all ordered field from the list of names
        for field_name in cls.field_order:
            if field_name not in field_names:
                raise ValueError(f"{field_name} is in field_order but is not a valid field.")
            field_names.remove(field_name)

        for field_name in cls.field_order + field_names:
            _fields[field_name] = getattr(cls, field_name)

        return _fields

    @classmethod
    def get_queryset(cls, filter):
        """Return a queryset matching the dynamic group filter.

        By default the queryset is generated based of the filterset but this is not mandatory
        """
        filterset = cls.filterset(cls.get_filterset_params(filter), cls.model.objects.all())
        return filterset.qs

    @classmethod
    def get_filterset_params(cls, filter):
        return filter

    @classmethod
    def get_filterset_as_string(cls, filter):
        """Get filterset as string."""
        if not filter:
            return None

        result = ""

        for key, value in cls.get_filterset_params(filter).items():
            if isinstance(value, list):
                for item in value:
                    if result != "":
                        result += "&"
                    result += f"{key}={item}"
            else:
                result += "&"
                result += f"{key}={value}"

        return result

    @classmethod
    def get_group_queryset_filter(cls, obj):
        raise NotImplementedError
