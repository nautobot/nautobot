from importlib import import_module
import logging
import sys

logger = logging.getLogger(__name__)


def flush_module(base_module_name, reimport=True):
    """
    Attempt to unload (and possibly reimport) a named module and any submodules.

    Caveat: this is a hard problem to solve in Python; this particular implementation is really only designed for use
    with loading and reloading of Jobs in `JOBS_ROOT` or Jobs provided by a GitRepository.

    **Use for any other purpose at your own risk.**

    Note that Django `runserver` autoreload uses a much more blunt-force approach; it literally does a `sys.exit()` on
    detecting any file change.
    """
    modules_to_reimport = [base_module_name]
    for module_name in list(sys.modules):
        if module_name == base_module_name or module_name.startswith(f"{base_module_name}."):
            logger.debug("Unloading module %s", module_name)
            del sys.modules[module_name]
            if module_name not in modules_to_reimport:
                modules_to_reimport.append(module_name)

    if reimport:
        for module_name in modules_to_reimport:
            try:
                logger.debug("Importing module %s", module_name)
                import_module(module_name)
            except ModuleNotFoundError:
                # Maybe it no longer exists?
                logger.warning("Unable to find module %s to re-import it after unloading it", module_name)
            except Exception as exc:
                # More problematic!
                logger.error("Unable to import module %s: %s", module_name, exc)
                raise
