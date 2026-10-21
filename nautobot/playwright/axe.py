"""axe-core accessibility scans for Playwright tests.

`assert_no_accessibility_violations(page)` loads axe-core into the page that the test has open,
runs the WCAG rules that Nautobot checks, and fails with the violations. The scan settings and
the axe-core loader are copies of the ones in `nautobot/core/testing/axe.py`, which the Selenium
tests use. They are copied rather than imported because the Playwright suite is black-box. It
does not import `nautobot.core`, whose `__init__` imports the Celery app, which reads Django settings.
"""

import base64
import functools
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile

import requests

# `nautobot/`, the package directory. `settings.BASE_DIR` resolves to the same path in the Selenium loader.
NAUTOBOT_DIR = Path(__file__).resolve().parent.parent

AXE_CORE_PATH = NAUTOBOT_DIR / "ui" / "node_modules" / "axe-core" / "axe.min.js"

PACKAGE_LOCK_PATH = NAUTOBOT_DIR / "ui" / "package-lock.json"

AXE_CORE_DOWNLOAD_TIMEOUT = 30

# WCAG 2.2 A and AA. The earlier tags are needed too: axe tags each rule with the version that introduced it, so
# `wcag22*` alone matches only `target-size`. Selecting by tag also runs `target-size`, which axe disables by default.
AXE_DEFAULT_TAGS = ("wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa")

# Impact is how badly a violation affects a user, not how important the criterion is. `meta-viewport` is a WCAG AA
# failure reported at `moderate`. Narrowing this list hides conformance failures.
AXE_DEFAULT_IMPACTS = ("critical", "serious", "moderate", "minor")

# django-debug-toolbar's container. The suite sends `X-Disable-Debug-Toolbar` on every request (see `fixtures.py`), so
# this exclusion matters only for scans run by hand against a development instance.
AXE_EXCLUDE_SELECTORS = ("#djDebugRoot",)

# `color-contrast` is a WCAG 1.4.3 AA rule and the theme currently fails it in several places. Fixing it means retuning
# palette tokens, which is a product decision that has been deferred, so the rule is off rather than left failing.
AXE_DISABLED_RULES = ("color-contrast",)

# The first few offenders per rule are enough to act on.
MAX_NODES_PER_VIOLATION = 5


_AXE_RUN_SCRIPT = """
([context, exclude, tags, disabledRules]) => {
    /* `include`/`exclude` take arrays of selector arrays, so pass bare `document` rather than including it. */
    const axeContext = {};
    if (context) { axeContext.include = [[context]]; }
    if (exclude && exclude.length) { axeContext.exclude = exclude.map((selector) => [selector]); }
    const axeOptions = { runOnly: { type: 'tag', values: tags } };
    if (disabledRules.length) {
        axeOptions.rules = Object.fromEntries(disabledRules.map((rule) => [rule, { enabled: false }]));
    }
    return axe.run(Object.keys(axeContext).length ? axeContext : document, axeOptions)
        .then((results) => ({ violations: results.violations }));
}
"""


class AccessibilityViolations(AssertionError):
    """The scanned page has axe-core violations at the impact levels that the scan checks."""


def _extract_axe_core(tarball, origin):
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
        try:
            file = archive.extractfile("package/axe.min.js")
        except KeyError as error:
            raise RuntimeError(f"axe-core from {origin} contains no package/axe.min.js.") from error
        return file.read()


def _write_axe_core_cache(tarball, cache_path):
    try:
        file_descriptor, partial_path = tempfile.mkstemp(dir=cache_path.parent, prefix=f"{cache_path.name}.")
    except OSError:
        return

    try:
        with os.fdopen(file_descriptor, "wb") as file:
            file.write(tarball)
        os.replace(partial_path, cache_path)
    except OSError:
        Path(partial_path).unlink(missing_ok=True)


def _verify_axe_core_integrity(tarball, integrity, origin):
    digests = dict(entry.split("-", 1) for entry in integrity.split() if "-" in entry)
    expected_digest = digests.get("sha512")
    if expected_digest is None:
        raise RuntimeError(f"axe-core integrity in {PACKAGE_LOCK_PATH} has no sha512: {integrity!r}.")

    digest = base64.b64encode(hashlib.sha512(tarball).digest()).decode("ascii")
    if digest != expected_digest:
        raise RuntimeError(f"axe-core from {origin} does not match the digest pinned in {PACKAGE_LOCK_PATH}.")


def _download_axe_core(url, integrity):
    # `requests` reads HTTP(S)_PROXY from the environment, so a proxied host needs no extra setting.
    try:
        response = requests.get(url, timeout=AXE_CORE_DOWNLOAD_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"axe-core could not be downloaded from {url}: {error}") from error

    _verify_axe_core_integrity(response.content, integrity, url)
    return response.content


def _read_axe_core_cache(cache_path, integrity):
    try:
        tarball = cache_path.read_bytes()
        _verify_axe_core_integrity(tarball, integrity, cache_path)
    except (OSError, RuntimeError):
        return None
    return tarball


def _read_installed_axe_core(version):
    try:
        package = json.loads((AXE_CORE_PATH.parent / "package.json").read_text(encoding="utf-8"))
        if package["version"] != version:
            return None
        return AXE_CORE_PATH.read_text(encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _get_axe_core_metadata():
    try:
        package_lock = json.loads(PACKAGE_LOCK_PATH.read_text(encoding="utf-8"))
        metadata = package_lock["packages"]["node_modules/axe-core"]
        entry = metadata["version"], metadata["resolved"], metadata["integrity"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RuntimeError(f"{PACKAGE_LOCK_PATH} has no readable axe-core entry: {error}") from error

    if not all(isinstance(value, str) and value for value in entry):
        raise RuntimeError(f"{PACKAGE_LOCK_PATH} has an incomplete axe-core entry: {entry}.")
    return entry


@functools.cache
def _load_axe_core_source():
    try:
        version, url, integrity = _get_axe_core_metadata()
        source = _read_installed_axe_core(version)
        if source is not None:
            return source, None

        cache_path = Path(tempfile.gettempdir()) / f"nautobot-axe-core-{os.getuid()}-{version}.tgz"
        tarball = _read_axe_core_cache(cache_path, integrity)
        if tarball is None:
            tarball = _download_axe_core(url, integrity)
            _write_axe_core_cache(tarball, cache_path)
        return _extract_axe_core(tarball, url).decode("utf-8"), None
    except RuntimeError as error:
        return None, str(error)


def get_axe_core_source():
    """Return the `axe.min.js` source at the version `nautobot/ui/package-lock.json` pins.

    Reads the installed copy under `nautobot/ui/node_modules` when its version matches. Otherwise
    downloads the pinned tarball from the registry, checks it against the lockfile's sha512, and
    caches it in the temp directory. Raises `RuntimeError` when no verified copy is available.
    """
    source, error_message = _load_axe_core_source()
    if error_message is not None:
        raise RuntimeError(error_message)
    return source


def run_axe(
    page, context=None, exclude=AXE_EXCLUDE_SELECTORS, tags=AXE_DEFAULT_TAGS, disabled_rules=AXE_DISABLED_RULES
):
    """Run axe-core on the page that the test has open and return its `violations` list, unfiltered.

    `context` limits the scan to a CSS selector, `exclude` removes selectors from it, and `disabled_rules`
    lists rules that are not run at all. Pass `()` to scan with everything the tags select.
    """
    # Every API call that passes the source is recorded in the trace with it, 570 KB each time. A test that
    # scans many pages uses the `axe_core_on_load` fixture, which records the source once per test instead.
    if page.evaluate("typeof axe === 'undefined'"):
        page.evaluate(get_axe_core_source())
    # `page.evaluate` awaits the promise `axe.run` returns.
    results = page.evaluate(_AXE_RUN_SCRIPT, [context, list(exclude or ()), list(tags), list(disabled_rules or ())])
    return results["violations"]


def format_violations(violations):
    """Return one block of text per violation: impact, rule, help text, help URL, and the first offending selectors."""
    lines = []
    for violation in violations:
        lines.append(f"  [{violation['impact']}] {violation['id']}: {violation['help']}")
        lines.append(f"    {violation['helpUrl']}")
        for node in violation.get("nodes", [])[:MAX_NODES_PER_VIOLATION]:
            lines.append(f"    at {', '.join(node.get('target', []))}")
    return "\n".join(lines)


def assert_no_accessibility_violations(
    page,
    impacts=AXE_DEFAULT_IMPACTS,
    tags=AXE_DEFAULT_TAGS,
    context=None,
    exclude=AXE_EXCLUDE_SELECTORS,
    disabled_rules=AXE_DISABLED_RULES,
):
    """Fail with `AccessibilityViolations` if the page that the test has open has axe-core violations at the given impacts.

    Scan the page only after an element that the view itself renders is present. Nautobot's error pages have
    the same `main` as every other page, so a wait on `main` lets a failed view be scanned as its error page.

    Only violations are reported. axe's `incomplete` bucket, the checks it could not decide, needs a human.
    Read it with a browser extension (see "Scanning by hand" in `docs/development/core/ui-best-practices.md`).
    Do not assume an entry there is a checker limitation. Contrast is indeterminate for any part of an element
    falling outside the ancestor that paints its background, so a label overflowing its container reports as
    undecidable when it is really a layout bug.
    """
    violations = [
        violation
        for violation in run_axe(page, context=context, exclude=exclude, tags=tags, disabled_rules=disabled_rules)
        if violation.get("impact") in impacts
    ]
    if violations:
        raise AccessibilityViolations(
            f"{len(violations)} accessibility violation(s) at impact {impacts} on {page.url}:\n"
            f"{format_violations(violations)}"
        )
