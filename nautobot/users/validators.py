from django.core.exceptions import ValidationError
from django.utils.http import url_has_allowed_host_and_scheme


def validate_relative_url(value):
    if not value.startswith("/") or not url_has_allowed_host_and_scheme(url=value, allowed_hosts=None):
        raise ValidationError("Enter a URL relative to this Nautobot instance, such as /dcim/devices/.")


def validate_navbar_favorites(value):
    if not isinstance(value, list):
        raise ValidationError("Navbar favorites must be a list.")

    for item in value:
        if not isinstance(item, dict):
            raise ValidationError("Each navbar favorite must be an object.")
        for key in ("link", "name"):
            if not isinstance(item.get(key), str) or not item[key]:
                raise ValidationError(f"Each navbar favorite requires a non-empty {key}.")
        if not isinstance(item.get("tab_name", ""), str):
            raise ValidationError("A navbar favorite tab name must be a string.")
        validate_relative_url(item["link"])
