"""Plain helper functions for the Playwright test suite.

Ordinary functions, imported normally. Fixtures (anything pytest constructs
per test, with dependencies or teardown) live in `fixtures.py`.
"""

from uuid import uuid4


def unique_name(prefix="ZZZ-test"):
    """Return a unique, sortable name for a test-owned record.

    The prefix sorts owned records last; the hex suffix keeps parallel runs and
    repeated runs against a shared instance from colliding.
    """
    return f"{prefix}-{uuid4().hex[:8]}"
