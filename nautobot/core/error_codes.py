from collections import namedtuple
from textwrap import dedent
from typing import Tuple, Any

from nautobot.extras.registry import registry

ErrorCode = namedtuple("ErrorCode", ["troubleshooting", "description", "error_message", "recommendation"])

registry["error_codes"] = {}


def register_error_codes(error_details: Tuple[str, ErrorCode]) -> None:
    """
    Register an error code in the central registry.

    Args:
        error_details: A tuple of (error_code, ErrorCode object) to register.

    Raises:
        ValueError: If the error code is already registered or invalid.
    """
    error_code, error_obj = error_details

    # Validate input
    if not isinstance(error_code, str):
        raise ValueError("Error code must be a string.")
    if not isinstance(error_obj, ErrorCode):
        raise ValueError("Error object must be an instance of ErrorCode.")
    if error_code in registry["error_codes"]:
        raise ValueError(f"Error code '{error_code}' is already registered.")

    registry["error_codes"][error_code] = error_obj


def error_message(error_code: str, **kwargs: Any) -> str:
    """Get the error message for a given error code.

    Args:
        error_code: The error code.
        **kwargs: Any additional context data to be interpolated in the error message.

    Returns:
        The constructed error message.
    """
    if not registry["error_codes"].get(error_code):
        return f"{error_code}: Error code not found in registry."
    try:
        error_message = registry["error_codes"][error_code].error_message.format(**kwargs)
    except KeyError as missing_kwarg:
        error_message = f"Error Code was found, but failed to format, message expected kwarg `{missing_kwarg}`."
    except Exception:  # pylint: disable=broad-except
        error_message = "Error Code was found, but failed to format message, unknown cause."
    return f"`{error_code}`: {error_message}"


E0001 = ErrorCode(
    troubleshooting=dedent("""\
        The range format must be a string, such as '0-3,5'. It should not be:

        - 0-3,5-
        - 10-3,5-30
        """),
    description="When creating numeric ranges, such as in VLANGroups, must follow a set of rules.",
    error_message="Input value must be a string using a range format, `{input_string}` is not valid.",
    recommendation="Review the range and ensure it is valid, removing all additional whitespace.",
)

E0002 = ErrorCode(
    troubleshooting=dedent("""\
        This is our 2nd error code.
        """),
    description="This is our 2nd error code.",
    error_message="This is our 2nd error code.",
    recommendation="This is our 2nd error code.",
)

E0003 = ErrorCode(
    troubleshooting=dedent("""\
        This is our 3rd error code.
        """),
    description="This is our 3rd error code.",
    error_message="This is our 3rd error code.",
    recommendation="This is our 3rd error code.",
)

register_error_codes(("E0001", E0001))
register_error_codes(("E0002", E0002))
register_error_codes(("E0003", E0003))