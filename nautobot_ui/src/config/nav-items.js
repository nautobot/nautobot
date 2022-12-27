import { GenericListView } from "@nautobot/components"
import { MarketPlace } from "@nautobot/views"
import { DeviceRetriveView } from "@nautobot/views/dcim"

// Import plugin navigations
import {navigation as tabline_one_nav} from "@tabline_one/navigation"
// import material_ui_plugin_navigation from "@material_plugin/config"


// End plugin navigations


// Add installed plugins here
const installed_plugins = [
    {
        path: "tabline-one",
        navgation: tabline_one_nav,
    }
]

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

function build_navigation(){
    let new_nav = navigation_menu
    const exclude = ["__home",]
    
    // prepend `plugins/plugin-path/` all plugin routes path
    // Then add the plugin nav objects to navigation menu
    installed_plugins.forEach(plugin => {
        Object.entries(plugin.navgation).forEach(nav => {
            let [nav_name, nav_object] = nav
            if (exclude.includes(nav_name)) return
            
            const new_nav_object = nav_object.map(nav_group => {
                    return {
                        ...nav_group, 
                        items: nav_group.items.map(route => {
                            return {...route, path: `plugins/${plugin.path}/${route.path}`}
                        })
                    }
                })
            

            // We either add this menu to main menu or to plugins dropdown
            if (nav_name === "__plugin_nav"){
                // Add items in __plugin to new_nav["Plugins"];
                // By doing this, we can have this plugin group showing as a dropdown in
                // Plugins
                new_nav["Plugins"] = [...new_nav["Plugins"], ...new_nav_object]
            }
            else {
                // Add plugin nav to navigation menu
                new_nav[nav_name] = new_nav_object
            }
        })
    })
    return new_nav
}


function get_navigation() {
    let all_navigations = {
        ...tabline_one_nav,
        ...navigation_menu,
    }
    return all_navigations
}


// Get only navigations meant to be on the navbar
const nav_bar_navigation = Object.entries(build_navigation()).filter(item => !item[0].startsWith("__"))

export { get_navigation, nav_bar_navigation }