from django_extensions.db.fields import AutoSlugField as _AutoSlugField


class AutoSlugField(_AutoSlugField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 100)
        kwargs.setdefault("editable", True)
        kwargs.setdefault("overwrite_on_add", False)
        kwargs.setdefault("unique", True)
        super().__init__(*args, **kwargs)
