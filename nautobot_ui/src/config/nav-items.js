import { GenericListView } from "@nautobot/components"
import { MarketPlace } from "@nautobot/views"
import { DeviceRetriveView } from "@nautobot/views/dcim"

const navigation_menu = {
    "Organization": [
        {
            name: "Sites",
            items: [
                {
                    "name": "Sites",
                    "path": "dcim/sites",
                    "model": "dcim.site",
                    "icons": {
                        "plus": { "action": "create" },
                        "database-in": { "action": "import" },
                    }
                },
                {
                    "name": "Region",
                    "path": "dcim/regions",
                    "model": "dcim.region",
                    "views":
                    {
                        "list": {},
                        "retrieve": {},
                    },
                    "icons": {
                        "plus": { "action": "create" },
                        "database-in": { "action": "import" },
                    }
                }
            ]
        },
        {
            name: "Statuses",
            items: [
                {
                    "name": "Statuses",
                    "path": "extras/statuses",
                    "model": "extras.status",
                    "icons": {
                        "plus": { "action": "create" }
                    }
                }
            ]
        }
    ],
    "Devices": [
        {
            name: "Devices",
            items: [
                {
                    "name": "Devices",
                    "path": "dcim/devices",
                    "model": "dcim.device",
                    "views": {
                        "list": {
                            "component": GenericListView,
                            "model": "dcim.sites"
                        },
                        "retrieve": {
                            "component": DeviceRetriveView,
                        },
                        "delete": {},
                        "create": {},
                    },
                    "icons": {
                        "plus": { "action": "create" },
                        "database-out": { "action": "export" },
                        "database-in": { "action": "import" },
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
    "Plugins": [
        {
            name: "General",
            items: [
                {
                    "name": "Insalled Plugins",
                    "path": "plugins/installed-plugins",
                    "model": "dcim.device",
                    "views": {
                        "list": {
                            "component": GenericListView,
                            "model": "dcim.sites"
                        },
                    },
                },
                {
                    "name": "Market Place",
                    "path": "plugins/market-place",
                    "views": {
                        "list": {
                            "component": MarketPlace
                        },
                    },
                },

            ]
        }
    ],
}

function get_navigation(plugin) {
    return navigation_menu
}

export { get_navigation }