from django.contrib import messages
from django.utils.html import format_html, format_html_join


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
    err_message += format_html_join(
        ", ",
        '<a href="{}">{}</a>',
        ((dependent.get_absolute_url(), dependent) for dependent in protected_objects[:50]),
    )

    messages.error(request, err_message)
