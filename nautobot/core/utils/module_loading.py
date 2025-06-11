from contextlib import contextmanager
import importlib
from importlib.util import find_spec, module_from_spec
from keyword import iskeyword
import logging
import os
import pkgutil
import sys

logger = logging.getLogger(__name__)


def clear_module_from_sys_modules(module_name):
    """
    Remove the module and all its submodules from sys.modules.
    """
    for name in list(sys.modules.keys()):
        if name == module_name or name.startswith(f"{module_name}."):
            del sys.modules[name]


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
    if any([module_info.name == name for module_info in pkgutil.iter_modules()]):
        return False, "the name of an installed Python package"
    return True, "a valid and non-conflicting module name"


def import_modules_privately(path, module_path=None, module_prefix="", ignore_import_errors=True):
    """
    Import modules from the filesystem without adding the path permanently to `sys.path`.

    This is used for importing Jobs from `JOBS_ROOT` and `GIT_ROOT` in such a way that they remain relatively
    self-contained and can be easily discarded and reloaded on the fly.

    If you find yourself writing new code that uses this method, please pause and reconsider your life choices.

    Args:
        path (str): Directory path possibly containing Python modules or packages to load.
        module_path (list): If set to a non-empty list, only modules matching the given chain of modules will be loaded.
            For example, `["my_git_repo", "jobs"]`.
        module_prefix (str): For recursive import - the containing module, if any, for example "my_git_repo" or
            "my_git_repo.jobs". Generally should be omitted when calling this method directly.
        ignore_import_errors (bool): Exceptions raised while importing modules will be caught and logged.
            If this is set as False, they will then be re-raised to be handled by the caller of this function.
    """
    # We formerly used pkgutil.walk_packages() here to handle recursive loading, but that has the downside (and risk!) of
    # automatically importing all packages that it finds in the given path, whether or not we actually want to do so.
    # So instead, we use pkgutil.iter_modules() to only discover top-level modules, and recurse ourselves as needed.
    for finder, discovered_module_name, is_package in pkgutil.iter_modules([path]):
        if module_path and discovered_module_name != module_path[0]:
            continue  # This is not the droid we're looking for

        if not module_prefix:  # only needed for top-level packages, submodules can presume the base module was already safe
            permitted, reason = check_name_safe_to_import_privately(discovered_module_name)
            if not permitted:
                logger.error("Unable to load module %r from %s as it is %s", discovered_module_name, path, reason)
                continue
            module_name = discovered_module_name
            if module_name in sys.modules:
                clear_module_from_sys_modules(module_name)
        else:
            module_name = f"{module_prefix}.{discovered_module_name}"

        try:
            spec = finder.find_spec(discovered_module_name)
            if spec is None:
                raise ValueError("Unable to find module spec")
            module = module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception as exc:
            logger.error("Unable to load module %s from %s: %s", discovered_module_name, path, exc)
            if not ignore_import_errors:
                raise
            module = None

        if module is not None and is_package and module_path:
            import_modules_privately(
                path=os.path.join(path, module_path[0]),
                module_path=module_path[1:],
                module_prefix=module_path[0],
                ignore_import_errors=ignore_import_errors,
            )
