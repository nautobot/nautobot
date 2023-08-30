import { Suspense } from "react";
import { lazy } from "react";
import { getComponentFromModule } from "./app-import";
import { LoadingWidget } from "@components/LoadingWidget";

const nautobot_config = require("../nautobot.config.json");

let app_routes = {};
try {
    app_routes = require("@generated/app_routes.json");
} catch {}

export function getPluginRoutes() {
    let react_routes = [];

    for (const [app_name, routes] of Object.entries(app_routes)) {
        for (const { path, component } of routes) {
            const Component = lazy(() =>
                getComponentFromModule(app_name, component)
            );
            const route_data = {
                path,
                element: (
                    <Suspense fallback={<LoadingWidget />}>
                        <Component />
                    </Suspense>
                ),
            };
            react_routes.push(route_data);
        }
    }

    return react_routes;
}

/**
 * Return true if `route` is part of the routes enabled for new-ui.
 */
export const isEnabledRoute = (route) =>
    process.env.NODE_ENV === "development" ||
    nautobot_config["enabled-routes"].includes(route);

/**
 * Return true if `context` has children routes which are part of the enabled new-ui routes.
 */
export function isEnabledContextRoute(menuInfo, context_name) {
    if (process.env.NODE_ENV === "development") {
        return true;
    }

    let isEnabledContextRoute = false;
    const context = menuInfo[context_name];
    Object.entries(context).forEach(([_, sub_context]) => {
        Object.entries(sub_context).forEach(([_, url]) => {
            if (isEnabledRoute(url)) {
                isEnabledContextRoute = true;
            }
        });
    });
    return isEnabledContextRoute;
}
