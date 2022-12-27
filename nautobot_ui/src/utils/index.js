import { GenericListView, GenericCreateView, GenericRetrieveView } from "@nautobot/components"

const { navbarNavigation, navigation } = require("@nautobot/config");
const { naxios } = require("./axios");


/**
 * Returns an object containing the view components for each CRUD action (list, create, retrieve).
 * If a custom component is specified for an action in the `data` object, that component will be used.
 * Otherwise, the default generic component for that action will be used.
 * 
 * @param {Object} data - An object containing custom view components for CRUD actions.
 * @returns {Object} An object containing the view components for each CRUD action.
 */
function getViewComponents(data) {
    // Default view components for each CRUD action
    let defaultViewComponents = {
        list: GenericListView,
        create: GenericCreateView,
        retrieve: GenericRetrieveView,
    }

    // If no custom view components are specified, return the default view components
    if (!data) return defaultViewComponents

    // Iterate over each CRUD action
    Object.keys(defaultViewComponents).forEach(action => {
        // If the action is not specified in the data object, set the view component to null
        if (!data[action]) {
            defaultViewComponents[action] = null;
        }
        // If a custom view component is specified for the action, use it
        else if (data[action].component) {
            defaultViewComponents[action] = data[action].component;
        }
        // Otherwise, use the default view component for the action
    });

    return defaultViewComponents;
}


/**
 * Converts the navigation menu object into an array of routes.
 * Special routes (i.e. those with a name starting with "__") are also included.
 * 
 * @param {Object} navbarNavigation - The navbar navigation object.
 * @param {Object} navigation - The navigation object.
 * @returns {Array} An array of route objects.
 */
function convertNavigationToRoute(navbarNavigation, navigation) {
    // Flat map the navbar navigation items and extract the "items" arrays
    const routeNavigations = navbarNavigation
        .flatMap(([_, navItems]) => navItems)
        .map(({ name, items }) => items)
        .flat();

    // Map the route navigation items to route objects
    const routes = routeNavigations.map(item => {
        // Get the view components for the item
        const viewsComponents = getViewComponents(item.views);
        return {
            path: item.path,
            element: <viewsComponents.list page_title={item.name} />,
        };
    });

    // Extract the special routes from the navigation object
    const specialMenu = Object.entries(navigation).filter(([name, _]) => name.startsWith("__")).map(([_, routeObject]) => routeObject);
    // Map the special routes to route objects
    const specialRoutes = specialMenu.map(routeGroup => {
        return routeGroup.map(routeObject => {
            return {
                path: routeObject.path,
                element: <routeObject.component />,
            };
        });
    });

    // Concatenate the regular and special
    return routes.concat(specialRoutes.flat());
}

const definedRoutes = convertNavigationToRoute(navbarNavigation, navigation)

export {
    convertNavigationToRoute,
    naxios,
    navbarNavigation,
    definedRoutes,
}

