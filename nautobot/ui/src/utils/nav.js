import NautobotApps from "../app_imports";
import { slugify } from "./string";

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

function get_routes() {
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
const pluginRoutes = get_routes();

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
    for (const [name, groups] of Object.entries(pluginRoutes)) {
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
