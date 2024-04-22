from contextlib import contextmanager
import importlib
from importlib.util import find_spec, module_from_spec
import logging
import os
import pkgutil
import sys

logger = logging.getLogger(__name__)


@contextmanager
def _temporarily_add_to_sys_path(path):
    """
    Allow loading of modules and packages from within the provided directory by temporarily modifying `sys.path`.

    On exit, it restores the original `sys.path` and `sys.modules` values.
    """
    old_sys_path = sys.path.copy()
    old_sys_modules = sys.modules.copy()
    sys.path.insert(0, path)
    try:
        yield
    finally:
        sys.path = old_sys_path
        sys.modules = old_sys_modules


def import_modules_privately(path, module_path=None, should_raise=False):
    """
    Import modules from the filesystem without adding them permanently to `sys.path` or `sys.modules`.

    This is used for importing Jobs from `JOBS_ROOT` and `GIT_ROOT` in such a way that they remain relatively
    self-contained and can be easily discarded and reloaded on the fly.

    If you find yourself writing new code that uses this method, please pause and reconsider your life choices.

    Args:
        path (str): Directory path possibly containing Python modules or packages to load.
        module_path (list): If set to a non-empty list, only modules matching the given chain of modules will be loaded.
            For example, `["my_git_repo", "jobs"]`.
        should_raise (bool): Whether any exception raised in importing modules should be re-raised to the caller.
    """
    if module_path is None:
        module_path = []
        module_prefix = None
    else:
        module_prefix = ".".join(module_path)
    with _temporarily_add_to_sys_path(path):
        for finder, discovered_module_name, is_package in pkgutil.walk_packages([path], onerror=logger.error):
            # logger.debug("Discovered module %s", discovered_module_name)
            if module_prefix and not (
                module_prefix.startswith(f"{discovered_module_name}.")  # my_repo/__init__.py
                or discovered_module_name == module_prefix  # my_repo/jobs.py
                or discovered_module_name.startswith(f"{module_prefix}.")  # my_repo/jobs/foobar.py
            ):
                # logger.debug("Skipping module %s", discovered_module_name)
                continue
            try:
                existing_module = find_spec(discovered_module_name)
            except ModuleNotFoundError:
                existing_module = None
            if existing_module is not None:
                existing_module_path = os.path.realpath(existing_module.origin)
                if not existing_module_path.startswith(path):
                    logger.error(
                        "Unable to load module %s from %s as it conflicts with existing module %s",
                        discovered_module_name,
                        path,
                        existing_module_path,
                    )
                    continue

            try:
                if not is_package:
                    spec = finder.find_spec(discovered_module_name)
                    if spec is None:
                        raise ValueError("Unable to find module spec")
                    module = module_from_spec(spec)
                    spec.loader.exec_module(module)
                else:
                    importlib.import_module(discovered_module_name)
            except Exception as exc:
                logger.error("Unable to load module %s from %s: %s", discovered_module_name, path, exc)
                if should_raise:
                    raise
