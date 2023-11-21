from django.contrib import messages
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe


def handle_protectederror(obj_list, request, e):
    """
    Generate a user-friendly error message in response to a ProtectedError exception.
    """
    protected_objects = list(e.protected_objects)
    protected_count = len(protected_objects) if len(protected_objects) <= 50 else "More than 50"
    err_message = format_html(
        "Unable to delete <strong>{}</strong>. {} dependent objects were found: ",
        ", ".join(str(obj) for obj in obj_list),
        protected_count,
    )

    # Append dependent objects to error message
    dependent_objects = []
    for dependent in protected_objects[:50]:
        if hasattr(dependent, "get_absolute_url"):
            dependent_objects.append(format_html('<a href="{}">{}</a>', dependent.get_absolute_url(), dependent))
        else:
            dependent_objects.append(escape(str(dependent)))
    err_message += mark_safe(", ".join(dependent_objects))  # noqa: S308

    messages.error(request, err_message)
