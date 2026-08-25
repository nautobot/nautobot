"""Helpers for request-local display-format preferences."""

from contextvars import ContextVar

TIME_FORMAT_12_HOUR = "12-hour"
TIME_FORMAT_24_HOUR = "24-hour"
TIME_FORMAT_PREFERENCES = frozenset({TIME_FORMAT_12_HOUR, TIME_FORMAT_24_HOUR})

_time_format_preference = ContextVar("nautobot_time_format_preference", default=None)


def get_time_format_preference():
    """Return the active request's preferred hour cycle, if any."""
    return _time_format_preference.get()


def set_time_format_preference(preference):
    """Set the active request's preferred hour cycle and return its ContextVar token."""
    if preference not in TIME_FORMAT_PREFERENCES:
        preference = None
    return _time_format_preference.set(preference)


def reset_time_format_preference(token):
    """Restore the hour-cycle preference that preceded ``token``."""
    _time_format_preference.reset(token)


def apply_time_format_preference(format_string, preference=None):
    """
    Rewrite a Django date/time format string for a 12-hour or 24-hour display.

    This intentionally changes only hour-cycle tokens. Date fields, separators,
    seconds, microseconds, and timezone tokens are otherwise preserved.
    Backslash-escaped format characters are left untouched.
    """
    if isinstance(format_string, PreferredTimeFormat):
        format_string = str.__str__(format_string)
    else:
        format_string = str(format_string)

    if preference is None:
        preference = get_time_format_preference()
    if preference not in TIME_FORMAT_PREFERENCES:
        return format_string

    output = []
    has_hour = False
    has_meridiem = False
    last_clock_output_index = None
    removed_meridiem = False
    index = 0

    while index < len(format_string):
        format_char = format_string[index]

        # Preserve escaped Django format characters as-is.
        if format_char == "\\" and index + 1 < len(format_string):
            output.append(format_string[index : index + 2])
            index += 2
            continue

        if preference == TIME_FORMAT_12_HOUR:
            if format_char in "gGhH":
                output.append("g")
                has_hour = True
                last_clock_output_index = len(output)
            elif format_char == "f":
                output.append(format_char)
                has_hour = True
                last_clock_output_index = len(output)
            elif format_char == "P":
                output.append(format_char)
                has_hour = True
                has_meridiem = True
                last_clock_output_index = len(output)
            else:
                output.append(format_char)
                if has_hour and format_char in {"i", "s", "u"}:
                    last_clock_output_index = len(output)
                if format_char in {"a", "A"}:
                    has_meridiem = True
        else:
            if format_char in "gGhH":
                output.append("H")
                has_hour = True
            elif format_char in {"f", "P"}:
                output.append("H:i")
                has_hour = True
            elif format_char in {"a", "A"}:
                removed_meridiem = True
                if output and output[-1].isspace():
                    output.pop()
            else:
                output.append(format_char)

        index += 1

    if preference == TIME_FORMAT_12_HOUR and has_hour and not has_meridiem and last_clock_output_index is not None:
        output.insert(last_clock_output_index, " a")

    result = "".join(output)
    return result.strip() if removed_meridiem else result


class PreferredTimeFormat(str):
    """
    A Django format string that resolves its hour cycle at render time.

    Django caches localized format objects. Keeping the cached value as this
    immutable ``str`` subclass while resolving ``__str__`` from a ContextVar
    lets concurrent requests use different user preferences safely.
    """

    def __str__(self):
        return apply_time_format_preference(str.__str__(self))
