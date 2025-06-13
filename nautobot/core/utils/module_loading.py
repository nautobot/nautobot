from importlib.machinery import FileFinder, SOURCE_SUFFIXES, SourceFileLoader
from importlib.util import module_from_spec
from keyword import iskeyword
import logging
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
    if any(module_info.name == name for module_info in pkgutil.iter_modules()):
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
        ignore_import_errors (bool): Exceptions raised while importing modules will be caught and logged.
            If this is set as False, they will then be re-raised to be handled by the caller of this function.
    """
    loaded_modules = []
    # We formerly used pkgutil.walk_packages() here to handle submodule loading with a multi-entry module_path,
    # but that has the downside (and risk!) of automatically importing all packages that it finds in the given path,
    # whether or not we actually want to do so. So instead, for the case where a module_path is provided, we need to
    # iteratively import each submodule ourselves.
    if module_path:
        # Git repository case - e.g. import_modules_privately(settings.GIT_ROOT, module_path=[repository_slug, "jobs"])
        # Here we want to ONLY auto-load the module sequence identified by module_path.
        permitted, reason = check_name_safe_to_import_privately(module_path[0])
        if not permitted:
            logger.error("Unable to load module %r from %s as it is %s", module_path[0], path, reason)
        else:
            module = None
            module_name = module_path.pop(0)
            submodule_name = module_name
            try:
                while True:
                    finder = FileFinder(path, (SourceFileLoader, SOURCE_SUFFIXES))
                    finder.invalidate_caches()
                    spec = finder.find_spec(module_name)
                    if spec is None or spec.loader is None:
                        logger.error("Unable to find module spec and/or loader for %r", submodule_name)
                        break
                    spec.name = submodule_name
                    spec.loader.name = submodule_name
                    submodule = module_from_spec(spec)
                    sys.modules[submodule_name] = submodule
                    spec.loader.exec_module(submodule)
                    if module is not None:
                        setattr(module, module_name, submodule)
                    module = submodule
                    loaded_modules.append(module)
                    if module_path:
                        submodule_name = f"{module_name}.{module_path[0]}"
                        module_name = module_path.pop(0)
                        path = module.__path__[0]
                    else:
                        break
            except Exception as exc:
                logger.error("Unable to load module %s from %s: %s", module_name, path, exc)
                if not ignore_import_errors:
                    raise
    else:
        # JOBS_ROOT case - import ALL top-level modules/packages that we can find in the given path;
        # they can implement and import submodules as desired by themselves, but we only autoimport top-level ones.
        for finder, discovered_module_name, _ in pkgutil.iter_modules([path]):
            permitted, reason = check_name_safe_to_import_privately(discovered_module_name)
            if not permitted:
                logger.error("Unable to load module %r from %s as it is %s", discovered_module_name, path, reason)
                continue
            module_name = discovered_module_name
            if module_name in sys.modules:
                clear_module_from_sys_modules(module_name)

            try:
                spec = finder.find_spec(discovered_module_name)
                if spec is None or spec.loader is None:
                    logger.error("Unable to find module spec and/or loader for %r", discovered_module_name)
                    continue
                module = module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                loaded_modules.append(module)
            except Exception as exc:
                logger.error("Unable to load module %s from %s: %s", discovered_module_name, path, exc)
                if not ignore_import_errors:
                    raise
    return loaded_modules
