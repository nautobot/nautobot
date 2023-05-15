import { Suspense } from "react";
import { lazy } from "react";
import { my_import_as_function } from "./app-import";
import { LoadingWidget } from "@components/LoadingWidget";

const app_routes = require("../app_routes.json")


export function getPluginRoutes() {
    let react_routes = [];
    for (const [app_name, routes] of Object.entries(app_routes)) {
        for (const {path, component} of routes) {
            const Component = lazy(() => my_import_as_function(app_name, component))
            const route_data = {
                path,
                element: <Suspense fallback={<LoadingWidget />} ><Component /></Suspense>,
            }
            react_routes.push(route_data);
        }
    }

    return react_routes;
}
