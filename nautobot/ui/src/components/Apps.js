import { lazy } from "react";

import NautobotApps from "../app_imports";
import { slugify } from "@utils/string";
import { my_import_as_function } from "@utils/utils";

function get_components() {
    var base = {};
    base["FullWidthComponents"] = {};
    base["CustomViews"] = {};
    base["OverrideViews"] = {};

    for (const [app_name, import_promise] of Object.entries(NautobotApps)) {
        import_promise.then((value) => {
            if (value?.default?.view_overrides) {
                // eslint-disable-next-line
                Object.entries(value.default.view_overrides).map(
                    ([route, views]) => {
                        // eslint-disable-next-line
                        return Object.entries(views).map(
                            ([view_action, component]) => {
                                if (!base["CustomViews"][route])
                                    base["CustomViews"][route] = {};
                                base["CustomViews"][route][view_action] = lazy(
                                    () =>
                                        my_import_as_function(
                                            app_name,
                                            component
                                        )
                                );
                                return true; // probably need to switch to using something other than map
                            }
                        );
                    }
                );
            }
            if (value?.default?.full_width_components) {
                // eslint-disable-next-line
                Object.entries(value.default.full_width_components).map(
                    ([route, components]) => {
                        if (!base["FullWidthComponents"][route]) {
                            base["FullWidthComponents"][route] = [];
                        }
                        // eslint-disable-next-line
                        components.map((component) => {
                            base["FullWidthComponents"][route].push(
                                lazy(() =>
                                    my_import_as_function(app_name, component)
                                )
                            );
                        });
                        return true; // probably need to switch to using something other than map
                    }
                );
            }
            // Add Plugin Provided View Components
            if (value?.default?.routes) {
                // eslint-disable-next-line
                value?.default?.routes.forEach(({ groups }) => {
                    groups.forEach(({ items }) => {
                        items.forEach(({ namespace, component }) => {
                            const route = `${slugify(app_name)}:${namespace}`;
                            base["OverrideViews"][route] = lazy(() =>
                                my_import_as_function(app_name, component)
                            );
                        });
                    });
                });
            }
        });
    }

    return base;
}

export default get_components();
