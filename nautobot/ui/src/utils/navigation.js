import { Suspense } from "react";
import { lazy } from "react";
import { getComponentFromModule } from "./app-import";
import { LoadingWidget } from "@components/LoadingWidget";

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
