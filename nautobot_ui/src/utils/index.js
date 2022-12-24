import { GenericListView, GenericCreateView, GenericRetrieveView } from "@nautobot/components"

const { get_navigation } = require("@nautobot/config");
const { naxios } = require("./axios");


function get_view_component(data){
    let views_components = {
        "list": GenericListView,
        "create": GenericCreateView,
        "retrieve": GenericRetrieveView,
    }
    // If not views; This means use generic views in all actions - [list, create, retrieve]
    if (!data) return views_components

    // List
    // This means list view is not a view
    Object.keys(views_components).forEach(action => {
        if (!data[action]) {
            // This action is ignored
            views_components[action] = null;
        }
        else if (data[action].component) {
            // Replace action generic view with desired action component
            views_components[action] = data[action].component;
        }
        // else leave the defualt generic component for that action
    })
    return views_components;
}


function convertNavigationToRoute() {
    const navigation = Object.values(get_navigation()).flatMap((groups) => groups.map(group => group.items)).flat();

    const routes = navigation.map(item => {
        let views_components =  get_view_component(item.views)
        return {
            path: item.path,
            element: <views_components.list page_title={item.name} />
        }
    })

    return routes;
}

export {
    convertNavigationToRoute,
    naxios,
    get_navigation,
}

