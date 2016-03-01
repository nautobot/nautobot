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

    # Handle multiple triggering objects
    if type(obj) in (list, tuple):
        messages.error(request, "Unable to delete the requested {}. The following dependent {} were found: {}".format(
            obj[0]._meta.verbose_name_plural,
            dep_class,
            ', '.join([str(o) for o in dependent_objects])
        ))

    # Handle a single triggering object
    else:
        messages.error(request, "Unable to delete {} {}. The following dependent {} were found: {}".format(
            obj._meta.verbose_name,
            obj,
            dep_class,
            ', '.join([str(o) for o in dependent_objects])
        ))
