from contextlib import contextmanager
import importlib
from importlib.util import find_spec
from keyword import iskeyword
import logging
import os
import pkgutil
import sys
import threading

from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

_import_lock = threading.RLock()


def import_string_optional(dotted_path):
    """An extension/wrapper of Django's `import_string()` that returns `None` if no such dotted path exists."""
    module_name, attribute_name = dotted_path.rsplit(".", 1)
    try:
        return import_string(dotted_path)
    except ModuleNotFoundError as err:
        # No such module
        if module_name.startswith(err.name):  # tried to import foo.bar.baz but couldn't find foo.bar, etc.
            return None
        # Some import *from within* the given module couldn't find what it was looking for?
        raise
    except ImportError as err:
        if isinstance(err.__cause__, AttributeError) and err.__cause__.name == attribute_name:  # pylint: disable=no-member
            # Exception raised by Django if the module exists but the *specific* requested attribute does not
            return None
        # Maybe a legitimate problem with the import?
        raise


@contextmanager
def _temporarily_add_to_sys_path(path):
    """
    Allow loading of modules and packages from within the provided directory by temporarily modifying `sys.path`.

    On exit, it restores the original `sys.path` value.
    """
    old_sys_path = sys.path.copy()
    sys.path.insert(0, path)
    try:
        yield
    finally:
        sys.path = old_sys_path


def check_name_safe_to_import_privately(name: str) -> tuple[bool, str]:
    """
    Make sure the given package/module name is "safe" to import from the filesystem.

    In other words, make sure it's:
    - a valid Python identifier and not a reserved keyword
    - not the name of an existing "real" Python package or builtin

    Returns:
        (bool, str): Whether safe to load, and an explanatory string fragment for logging/exception messages.
    """
    if not name.isidentifier():
        return False, "not a valid identifier"
    if iskeyword(name):
        return False, "a reserved keyword"
    if name in sys.builtin_module_names:
        return False, "a Python builtin"
    if any(module_info.name == name for module_info in pkgutil.iter_modules()):
        return False, "the name of an installed Python package"
    return True, "a valid and non-conflicting module name"


def import_modules_privately(path, module_path=None, ignore_import_errors=True):
    """
    Import modules from the filesystem without adding the path permanently to `sys.path`.

    This is used for importing Jobs from `JOBS_ROOT` and `GIT_ROOT` in such a way that they remain relatively
    self-contained and can be easily discarded and reloaded on the fly.

    Loading is done in four phases so that every class defined under `path` has exactly one object identity
    in `sys.modules` regardless of import order or where `register_jobs(...)` calls live in user code:

    1. Discover every module name under `path` (filtered by `module_path` if set) without importing.
    2. Bulk-clear all discovered names from `sys.modules` so there is no mixed-generation window.
    3. Import each top-level discovered name via the standard import machinery, letting transitive
       `from X import Y` cascades resolve to one consistent object per module.
    4. Sweep any discovered modules the cascade did not transitively load.

    If you find yourself writing new code that uses this method, please pause and reconsider your life choices.

    Args:
        path (str): Directory path possibly containing Python modules or packages to load.
        module_path (list): If set to a non-empty list, only modules matching the given chain of modules will be loaded.
            For example, `["my_git_repo", "jobs"]`.
        ignore_import_errors (bool): Exceptions raised while importing modules will be caught and logged.
            If this is set as False, they will then be re-raised to be handled by the caller of this function.
    """
    module_prefix = ".".join(module_path) if module_path else None

    with _import_lock, _temporarily_add_to_sys_path(path):
        # Phase 1: discover module names without importing.
        discovered = []
        for _finder, name, _is_package in pkgutil.walk_packages([path], onerror=logger.error):
            if module_prefix and not (
                module_prefix.startswith(f"{name}.")  # ancestor of the target, e.g. my_repo/__init__.py
                or name == module_prefix  # exact match, e.g. my_repo/jobs.py
                or name.startswith(f"{module_prefix}.")  # descendant, e.g. my_repo/jobs/foobar.py
            ):
                continue
            try:
                existing_module = find_spec(name)
            except (ModuleNotFoundError, ValueError):
                existing_module = None
            if existing_module is not None and existing_module.origin:
                existing_module_path = os.path.realpath(existing_module.origin)
                if not existing_module_path.startswith(path):
                    logger.error(
                        "Unable to load module %s from %s as it conflicts with existing module %s",
                        name,
                        path,
                        existing_module_path,
                    )
                    continue
            discovered.append(name)

        if not discovered:
            return []

        # Phase 2: single bulk clear of every name we are about to load.
        discovered_set = set(discovered)
        for cached in list(sys.modules):
            if cached in discovered_set or any(cached.startswith(f"{n}.") for n in discovered):
                del sys.modules[cached]

        loaded_modules = []

        # Phase 3: import each top-level discovered name once. Python's import machinery resolves
        # transitive `from X import Y` cascades, so every shared dependency lands in sys.modules
        # exactly once.
        top_level_names = sorted({n for n in discovered if "." not in n})
        for name in top_level_names:
            try:
                loaded_modules.append(importlib.import_module(name))
            except Exception as exc:
                logger.error("Unable to load module %s from %s: %s", name, path, exc)
                if not ignore_import_errors:
                    raise

        # Phase 4: any discovered module the cascade did not transitively touch is loaded here.
        # By now sys.modules has consistent versions of every shared dependency, so these cannot
        # create divergent class objects.
        for name in discovered:
            if name in sys.modules:
                continue
            try:
                loaded_modules.append(importlib.import_module(name))
            except Exception as exc:
                logger.error("Unable to load module %s from %s: %s", name, path, exc)
                if not ignore_import_errors:
                    raise

    return loaded_modules
