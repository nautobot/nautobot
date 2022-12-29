import { GenericListView } from "@nautobot/components"
import { MarketPlace } from "@nautobot/views"
import { DeviceRetriveView } from "@nautobot/views/dcim"

// __inject_import__

// End __inject_import__



const installed_plugins = [
    // Add installed plugins here: __inject_installed_plugins__
    
    // End __inject_installed_plugins__
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

/**
 * Builds the navigation menu by adding plugin routes to the main navigation menu.
 * Plugin routes are prepended with the plugin's path and added to either the main
 * navigation menu or the "Plugins" dropdown, depending on the plugin's configuration.
 * 
 * @param {Object} navigation_menu - The base navigation menu object.
 * @param {Array} installed_plugins - An array of objects representing installed plugins.
 * Each object should have a "navigation" property containing the plugin's navigation configuration.
 * 
 * @returns {Object} The updated navigation menu object.
 */
function buildNavigation(navigation_menu, installed_plugins) {
    // Make a copy of the base navigation menu
    let newNav = { ...navigation_menu };

    // These are special routes (e.g. "__home") that should not be added to the navbar
    const specialRoutes = ["__home",]

    // Iterate over each installed plugin
    installed_plugins.forEach(plugin => {
        // Iterate over each navigation item in the plugin
        Object.entries(plugin.navigation).forEach(([navName, navObject]) => {
            if (specialRoutes.includes(navName)) {
                let route_obj = {
                    "path": `plugins/${plugin.path}`,
                    "component": navObject
                }
                newNav[navName] = !newNav[navName] ? [route_obj] : [...newNav[navName], route_obj, ]
            }
            else {
                // Map over the navigation groups and items in the plugin's navigation configuration
                const newNavObject = navObject.map(navGroup => {
                    return {
                        ...navGroup,
                        items: navGroup.items.map(route => {
                            return { ...route, path: `plugins/${plugin.path}/${route.path}` }
                        })
                    }
                })


                // Add the plugin's navigation to the main navigation menu or the "Plugins" dropdown
                if (navName === "__plugin_nav") {
                    // Add the plugin's navigation items to the "Plugins" dropdown
                    newNav["Plugins"] = [...newNav["Plugins"], ...newNavObject]
                }
                else {
                    // Add the plugin's navigation to the main navigation menu
                    newNav[navName] = newNavObject
                }
            }
        });
    });
    return newNav;
}


// Build the navigation menu
const navigation = buildNavigation(navigation_menu, installed_plugins);

// Filter the navigation menu to get only the items that should be shown on the navbar
const navbarNavigation = Object.entries(navigation).filter(([name]) => !name.startsWith("__"));

export { navbarNavigation, navigation }
