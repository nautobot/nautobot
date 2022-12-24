import {GenericListView} from "@nautobot/components"
import {DeviceRetriveView} from "@nautobot/views/dcim"

const navigation = {
    "Organization": [
        {
            "Sites": [
                {
                    "name": "Sites",
                    "path": "dcim/sites",
                    "model": "dcim.site",
                    "views": ["list", "retrieve", "delete", "create", "update"],
                    "icons": {
                        "plus": {"action": "create"},
                        "database-in": {"action": "import"},
                    }
                },
                {
                    "name": "Region",
                    "path": "dcim/regions",
                    "model": "dcim.region",
                    "views": ["list", "retrieve", "delete", "create", "update"],
                    "icons": {
                        "plus": {"action": "create"},
                        "database-in": {"action": "import"},
                    }
                }
            ],
            "Statuses": [
                {
                    "name": "Statuses",
                    "path": "extras/statuses",
                    "model": "extras.status",
                    "views": ["list", "retrieve", "delete", "create", "update"],
                    "icons": {
                        "plus": {"action": "create"}
                    }
                }
            ]
        }
    ],
    "Devices": [
        {
            "Devices": [
                {
                    "name": "Devices",
                    "path": "dcim/sites",
                    "model": "dcim.site",
                    "views": [
                        {"list": <GenericListView model="dcim.sites" />}, 
                        {"retrieve": <DeviceRetriveView />},
                        "delete", 
                        "create", 
                        "update"
                    ],
                    "icons": {
                        "plus": {"action": "create"},
                        "database-out": {"action": "export"},
                        "database-in": {"action": "import"},
                    }
                },
                {
                    "name": "Platforms",
                    "path": "dcim/platforms",
                    "model": "dcim.platforms"
                }
            ]
        }
    ],
    "IPAM": [],
    "Virtualization": [],
    "Circuits": [],
    "Power": [],
    "Secrets": [],
    "Jobs": [],
    "Extensibility": [],
}