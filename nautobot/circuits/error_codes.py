from nautobot.core.error_codes import register_error_codes, ErrorCode
from textwrap import dedent

E0004 = ErrorCode(
    troubleshooting=dedent("""\
        This is our 4th error code.
        """),
    description="This is our 4th error code.",
    error_message="This is our 4th error code.",
    recommendation="This is our 4th error code.",
)

register_error_codes(("E0004", E0004))