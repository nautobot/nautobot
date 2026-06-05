# Suppressing Automatic Device/Module Component Creation

+++ 3.2.0

By default, when a new `Device` or `Module` is first saved, Nautobot calls `self.create_components()` from inside `save()` to instantiate one component (interface, console port, power port, rear/front port, device bay, module bay) per template defined on the related `DeviceType` / `ModuleType`. For apps that own the component inventory from an external source-of-truth and intend to write the full component graph themselves immediately after creating the parent object, this default is undesirable.

The `nautobot.apps.dcim.SkipAutoComponentCreation` context manager lets an app opt out for a scoped region of code.

## Usage

```python
from nautobot.apps.dcim import SkipAutoComponentCreation
from nautobot.dcim.models import Device

with SkipAutoComponentCreation():
    device = Device.objects.create(
        name="leaf-01",
        device_type=device_type,
        role=device_role,
        status=device_status,
        location=location,
    )
    # device.interfaces.count() == 0; no template-derived components were instantiated.
    # The app is now responsible for populating any components it needs.
```

The context manager:

- Suppresses `create_components()` on the **initial** `save()` of `Device` and `Module`. Subsequent saves of an existing instance are not affected — `create_components()` does not run on update saves regardless.
- Is **re-entrant**: nested `with` blocks restore the previous state (still suppressed) when the inner block exits, not the unconditional default.
- Is **exception-safe**: state is restored on exit even if the wrapped code raises.
- Is **task-scoped**: implemented via `contextvars.ContextVar`, so the flag is correctly isolated per asyncio task and per Celery worker invocation. A suppressing context in one Celery task does not leak into the next task that worker handles, and freshly spawned threads start with their own (default) context.

## Scope and limitations

| Path | Triggers default `create_components()`? | Honoured by `SkipAutoComponentCreation`? |
|---|---|---|
| `Device.objects.create(...)` / `Module.objects.create(...)` | Yes | Yes |
| `Device(...).save()` / `Module(...).save()` (new instance) | Yes | Yes |
| Subsequent `save()` of an existing instance (update/migrate/move) | No | N/A — nothing to suppress |
| `Device.objects.bulk_create([...])` / `Module.objects.bulk_create([...])` | No (bypasses `save()`) | N/A — nothing to suppress |

The context manager affects only the call from `Device.save()` / `Module.save()`. If an app calls `device.create_components()` directly, that explicit invocation is still honoured — `SkipAutoComponentCreation` gates the automatic call from inside `save()`, not the method itself.

!!! warning "Thread-based parallelization"
    Suppression is stored in a `contextvars.ContextVar`, which is **not** inherited by a separately spawned `threading.Thread` — each new thread starts from the default (unsuppressed). If you fan creation out across a thread pool (for example `concurrent.futures.ThreadPoolExecutor`), entering `with SkipAutoComponentCreation():` on the dispatching thread will **not** suppress component creation in the worker threads. In that case, enter the context manager *inside* each worker, or copy the calling context into the worker with `contextvars.copy_context()`. Asyncio-task and Celery-task scoping are unaffected.

## Introspection

`nautobot.apps.dcim.is_auto_component_creation_suppressed()` returns `True` if a `SkipAutoComponentCreation` context is currently active. This is primarily useful in tests and adapter code that wants to make conditional decisions based on the suppression state.

```python
from nautobot.apps.dcim import is_auto_component_creation_suppressed, SkipAutoComponentCreation

assert not is_auto_component_creation_suppressed()
with SkipAutoComponentCreation():
    assert is_auto_component_creation_suppressed()
```

Production code should normally use the context manager directly rather than checking the flag.
