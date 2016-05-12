from django.contrib import messages


def handle_protectederror(obj, request, e):
    """
    Generate a user-friendly error message in response to a ProtectedError exception.
    """
    dependent_objects = e[1]
    try:
        dep_class = dependent_objects[0]._meta.verbose_name_plural
    except IndexError:
        raise e

    # Grammar for single versus multiple triggering objects
    if type(obj) in (list, tuple):
        err_message = "Unable to delete the requested {}. The following dependent {} were found: ".format(
            obj[0]._meta.verbose_name_plural,
            dep_class,
        )
    else:
        err_message = "Unable to delete {} {}. The following dependent {} were found: ".format(
            obj._meta.verbose_name,
            obj,
            dep_class,
        )

    # Append dependent objects to error message
    dependent_objects = []
    for o in e[1]:
        if hasattr(o, 'get_absolute_url'):
            dependent_objects.append('<a href="{}">{}</a>'.format(o.get_absolute_url(), str(o)))
        else:
            dependent_objects.append(str(o))
    err_message += ', '.join(dependent_objects)

    messages.error(request, err_message)
