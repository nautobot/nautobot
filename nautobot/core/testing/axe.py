import base64
import functools
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile

from django.conf import settings
import requests

AXE_CORE_PATH = Path(settings.BASE_DIR) / "ui" / "node_modules" / "axe-core" / "axe.min.js"

PACKAGE_LOCK_PATH = Path(settings.BASE_DIR) / "ui" / "package-lock.json"

AXE_CORE_DOWNLOAD_TIMEOUT = 30

# WCAG 2.2 A and AA. The earlier tags are needed too: axe tags each rule with the version that introduced it, so
# `wcag22*` alone matches only `target-size` -- which selecting by tag also runs despite axe disabling it by default.
AXE_DEFAULT_TAGS = ("wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa")

# Impact is how badly a violation affects a user, not how important the criterion is: `meta-viewport` is a WCAG AA
# failure reported at `moderate`. Narrowing this hides conformance failures.
AXE_DEFAULT_IMPACTS = ("critical", "serious", "moderate", "minor")

# django-debug-toolbar's container. Dev-only dependency, added to `INSTALLED_APPS` under `if DEBUG` by the development
# configs, so no user can reach it. Tests run with `DEBUG` off; this is for scans run by hand.
AXE_EXCLUDE_SELECTORS = ("#djDebugRoot",)

# `color-contrast` is a WCAG 1.4.3 AA rule and the theme currently fails it in several places. Fixing it means retuning
# palette tokens, which is a product decision that has been deferred, so the rule is off rather than left failing.
AXE_DISABLED_RULES = ("color-contrast",)


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


def _read_installed_axe_core(version):
    try:
        package = json.loads((AXE_CORE_PATH.parent / "package.json").read_text(encoding="utf-8"))
        if package["version"] != version:
            return None
        return AXE_CORE_PATH.read_text(encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _verify_axe_core_integrity(tarball, integrity, origin):
    digests = dict(entry.split("-", 1) for entry in integrity.split() if "-" in entry)
    expected_digest = digests.get("sha512")
    if expected_digest is None:
        raise RuntimeError(f"axe-core integrity in {PACKAGE_LOCK_PATH} carries no sha512: {integrity!r}.")

    digest = base64.b64encode(hashlib.sha512(tarball).digest()).decode("ascii")
    if digest != expected_digest:
        raise RuntimeError(f"axe-core from {origin} does not match the digest pinned in {PACKAGE_LOCK_PATH}.")


def _extract_axe_core(tarball, origin):
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
        try:
            file = archive.extractfile("package/axe.min.js")
        except KeyError as error:
            raise RuntimeError(f"axe-core from {origin} contains no package/axe.min.js.") from error
        return file.read()


def _read_axe_core_cache(cache_path, integrity):
    try:
        tarball = cache_path.read_bytes()
        _verify_axe_core_integrity(tarball, integrity, cache_path)
    except (OSError, RuntimeError):
        return None
    return tarball


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


def _download_axe_core(url, integrity):
    try:
        response = requests.get(url, proxies=settings.HTTP_PROXIES, timeout=AXE_CORE_DOWNLOAD_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"axe-core could not be downloaded from {url}: {error}") from error

    _verify_axe_core_integrity(response.content, integrity, url)
    return response.content


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
    source, error_message = _load_axe_core_source()
    if error_message is not None:
        raise RuntimeError(error_message)
    return source
