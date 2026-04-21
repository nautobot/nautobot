---
name: ObjectChange permissions feature - issue 8694
description: Feature restricting ObjectChange list visibility from non-staff users seeing staff/superuser change log entries
type: project
---

Branch `u/sirisha-ObjectChangeUIViewSet-permissions` adds `get_queryset()` override to `ObjectChangeUIViewSet` in `nautobot/extras/views.py` that excludes changelog entries authored by staff/superusers when the requesting user is not staff. Changelog fragment is `changes/8694.changed`. The feature is intentionally scoped to the list/retrieve views (not `ObjectChangeLogView` per-object changelog tab).

**Why:** Security concern — non-staff users were able to see change log entries made by staff or superusers, which could expose sensitive operational information.

**How to apply:** When reviewing related changes, be aware this filter intentionally does NOT apply to `ObjectChangeLogView` (the per-object changelog tab) because that already goes through `restrict()`.
