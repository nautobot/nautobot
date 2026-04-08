from collections import Counter
from contextlib import contextmanager
import logging
import random
import re
import string

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.db.models import Q
from django.db.models.deletion import PROTECT
from django.test.utils import CaptureQueriesContext
from tree_queries.models import TreeNodeForeignKey

from nautobot.core.templatetags.helpers import bettertitle

# Use the proper swappable User model
User = get_user_model()


def post_data(data):
    """
    Take a dictionary of test data (suitable for comparison to an instance) and return a dict suitable for POSTing.
    """
    ret = {}

    for key, value in data.items():
        if value is None:
            ret[key] = ""
            ret.setdefault("_nullify", [])
            ret["_nullify"].append(key)
        elif isinstance(value, (list, tuple)):
            if value and hasattr(value[0], "pk"):
                # Value is a list of instances
                ret[key] = [v.pk for v in value]
            else:
                ret[key] = value
        elif hasattr(value, "pk"):
            # Value is an instance
            ret[key] = value.pk
        else:
            ret[key] = str(value)

    return ret


def create_test_user(username="testuser", permissions=None):
    """
    Create a User with the given permissions.
    """
    user = User.objects.create_user(username=username)
    if permissions is None:
        permissions = ()
    for perm_name in permissions:
        app, codename = perm_name.split(".")
        perm = Permission.objects.get(content_type__app_label=app, codename=codename)
        user.user_permissions.add(perm)

    return user


def extract_form_failures(content):
    """
    Given decoded HTML content from an HTTP response, return a list of form errors.
    """
    FORM_ERROR_REGEX = r"<!-- FORM-ERROR (.*) -->"
    return re.findall(FORM_ERROR_REGEX, content)


def extract_page_body(content):
    """
    Given raw HTML content from an HTTP response, extract the main div only.

    <html>
      <head>...</head>
      <body>
        <nav id="sidenav">...</nav><!-- BEGIN -->
        <header><nav><!-- breadcrumbs --></nav></header>
        <main class="container-fluid wrapper" id="main-content" tabindex="-1">
        ...
        </div><!-- END -->
        <footer class="footer">...</footer>
        ...
      </body>
    </html>
    """
    try:
        return re.findall(
            r"<nav id=\"sidenav\"[^>]*>.*?</nav>(.*?)(?=<footer)", content, flags=(re.MULTILINE | re.DOTALL)
        )[0]
    except IndexError:
        return content


def extract_page_title(content):
    """
    Given raw HTML content from an HTTP response, extract the page title section only.

    <div id="page-title" ...>...</header>
    """
    try:
        return re.findall(
            r"<div class=\"col-4\" id=\"page-title\">(.*?)(?=<\/header)", content, flags=(re.MULTILINE | re.DOTALL)
        )[0]
    except IndexError:
        return content


@contextmanager
def disable_warnings(logger_name):
    """
    Temporarily suppress expected warning messages to keep the test output clean.
    """
    logger = logging.getLogger(logger_name)
    current_level = logger.level
    logger.setLevel(logging.ERROR)
    yield
    logger.setLevel(current_level)


def get_deletable_objects(model, queryset):
    """
    Returns a subset of objects in the given queryset that have no protected relationships that would prevent deletion.
    """
    q = Q()
    for field in model._meta.get_fields(include_parents=True):
        if getattr(field, "on_delete", None) is PROTECT:
            q &= Q(**{f"{field.name}__isnull": True})
        # Only delete leaf nodes of trees to reduce complexity
        if isinstance(field, (TreeNodeForeignKey)):
            q &= Q(**{f"{field.related_query_name()}__isnull": True})
    return queryset.filter(q)


def generate_random_device_asset_tag_of_specified_size(size):
    """
    For testing purposes only; it returns a random string of size 100 consisting of letters and numbers.
    """
    asset_tag = "".join(random.choices(string.ascii_letters + string.digits, k=size))  # noqa: S311  # suspicious-non-cryptographic-random-usage
    return asset_tag


def get_expected_menu_item_name(view_model) -> str:
    """Return the expected menu item name for a given model."""
    name_map = {
        "Approval Workflow Definitions": "Workflow Definitions",
        "Approval Workflow Stages": "Approval Dashboard",
        "Controller Managed Device Groups": "Device Groups",
        "Object Changes": "Change Log",
        "Min Max Validation Rules": "Min/Max Rules",
        "Regular Expression Validation Rules": "Regex Rules",
        "Required Validation Rules": "Required Rules",
        "Unique Validation Rules": "Unique Rules",
        "VM Interfaces": "Interfaces",
    }

    expected = bettertitle(view_model._meta.verbose_name_plural)
    return name_map.get(expected, expected)


class AssertNoRepeatedQueries:
    """Context manager that detects N+1 query patterns by finding SQL templates that repeat excessively.

    Captures all SQL queries within the block, normalizes them (strips literal values to create
    structural templates), and flags any template that appears more than ``threshold`` times.

    Args:
        test_case: A ``unittest.TestCase`` instance whose ``.fail()`` will be called on violations.
        threshold: Maximum allowed repetitions of any single query template (default 10).

    Example::

        with AssertNoRepeatedQueries(self, threshold=10):
            execute_my_graphql_query()
    """

    _NORMALIZE_PATTERNS = [
        (re.compile(r"'[^']*'"), "'?'"),
        (re.compile(r"IN \([^)]+\)"), "IN (?)"),
    ]

    def __init__(self, test_case, threshold=10):
        self.test_case = test_case
        self.threshold = threshold
        self._context = CaptureQueriesContext(connection)
        self.captured_queries = []

    def __enter__(self):
        self._context.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._context.__exit__(exc_type, exc_val, exc_tb)
        if exc_type is not None:
            return False

        self.captured_queries = [q["sql"] for q in self._context.captured_queries]
        normalized = [self._normalize_sql(q) for q in self.captured_queries]
        counts = Counter(normalized)

        violations = {pattern: count for pattern, count in counts.items() if count > self.threshold}

        if violations:
            details = "\n".join(
                f"  [{count}x] {pattern[:300]}" for pattern, count in sorted(violations.items(), key=lambda x: -x[1])
            )
            self.test_case.fail(
                f"Detected N+1 query pattern(s) exceeding threshold of {self.threshold}:\n{details}\n"
                f"Total queries: {len(self.captured_queries)}"
            )
        return False

    @classmethod
    def _normalize_sql(cls, sql):
        """Replace literal values with placeholders so structurally identical queries share a key."""
        for pattern, replacement in cls._NORMALIZE_PATTERNS:
            sql = pattern.sub(replacement, sql)
        return sql
