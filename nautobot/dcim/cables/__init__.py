"""Service-layer helpers for cable operations that span more than one ``dcim.Cable`` row.

Currently this houses the "Bulk Connect" service, which creates N cables from a single
"template" cable plus a count, walking each side's natural termination ordering. See
``bulk_connect`` for details.
"""

from nautobot.dcim.cables.bulk_connect import (
    BulkCableConnectService,
    BulkConnectResult,
    BulkConnectSpec,
    ConnectorSelection,
    walk_terminations,
)

__all__ = (
    "BulkCableConnectService",
    "BulkConnectResult",
    "BulkConnectSpec",
    "ConnectorSelection",
    "walk_terminations",
)
