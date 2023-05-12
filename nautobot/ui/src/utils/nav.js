import NautobotApps from "../app_imports";
import { slugify } from "./string";
import { lazy } from "react";
import { my_import_as_function } from "./utils";

/**
 * Converts a plugin menu into a navigation menu format by grouping the items by name and group,
 * and appending the plugin name to the item path.
 *
 * @param {Array} data - The plugin menu to convert
 * @param {string} plugin_name - The name of the plugin to append to the item path
 * @param {Object} [finalData={}] - The initial navigation menu format data
 * @returns {Object} The navigation menu format data
 */

export function convertPluginMenuIntoNavMenuFormat(
    data,
    plugin_name,
    finalData = {}
) {
    for (const item of data) {
        const { name, groups } = item;

        if (!finalData[name]) {
            finalData[name] = {};
        }

        for (const group of groups) {
            const groupName = group.name;
            const { items } = group;

            if (!finalData[name][groupName]) {
                finalData[name][groupName] = {};
            }

            for (const item of items) {
                const itemName = item.name;
                const itemPath = item.path;
                finalData[name][groupName][
                    itemName
                ] = `/plugins/${plugin_name}${itemPath}`;
            }
        }
    }

    return finalData;
}

function getPluginNavMenu() {
    let data = {};
    for (const [app_name, import_promise] of Object.entries(NautobotApps)) {
        // eslint-disable-next-line no-loop-func
        import_promise.then((value) => {
            const routes = value?.default?.routes;
            if (routes) {
                data = convertPluginMenuIntoNavMenuFormat(
                    routes,
                    slugify(app_name),
                    data
                );
            }
        });
    }
    return data;
}
const pluginNavMenu = getPluginNavMenu();

/**
 * Updates the given navigation menu data with the plugin menu items.
 *
 * @param {Object} data - The navigation menu to update
 * @returns {Object} The updated navigation menu data
 */
export function updateMenuitemsWithPluginMenu(data) {
    // React Prevents modifying props; causing this error : cannot add property 'X', object is not extensible
    // Making a copy resolves the error
    let updatedData = JSON.parse(JSON.stringify(data));
    for (const [name, groups] of Object.entries(pluginNavMenu)) {
        if (!updatedData[name]) {
            updatedData[name] = {};
        }
        for (const [groupName, items] of Object.entries(groups)) {
            if (!updatedData[name][groupName] && name && groupName) {
                updatedData[name][groupName] = {};
            }
            Object.assign(updatedData[name][groupName], items);
        }
    }
    return updatedData;
}

/**
 * Converts a list of plugin routes to a list of React routes.
 *
 * @param {Array} data - A list of plugin routes to format:
 * @param {string} app_name - Plugin app_name.
 * @returns {Array} A list of React routes in the format:
 *   [
 *     {
 *       path: string,
 *       component: lazy(() => Component),
 *     },
 *     ...
 *   ]
 */
function convertPluginRoutesToReactRoutes(data, app_name) {
    let convertedData = [];
    data.forEach((namespace) => {
        namespace.groups.forEach((group) => {
            group.items.forEach((item) => {
                const path = `${slugify(app_name)}${item.path}`;
                const PluginComponent = lazy(() =>
                    my_import_as_function(app_name, item.component)
                );
                convertedData.push({ path, element: <PluginComponent /> });
            });
        });
    });
    return convertedData;
}

export async function getPluginRoutes() {
    let react_routes = [];
    for (const [app_name, import_promise] of Object.entries(NautobotApps)) {
        try {
            const pluginImports = await import_promise;
            const routes = pluginImports?.default?.routes;
            react_routes = convertPluginRoutesToReactRoutes(routes, app_name);
        } catch (e) {
            console.log("Encountered Error in importing Plugin Routes: ", e);
        }
    }
    return react_routes;
}
