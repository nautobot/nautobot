import { lazy } from "react";

import NautobotApps from "@generated/app_imports";
import { getComponentFromModule } from "../utils";

function get_components() {
    var base = {};
    base["FullWidthComponents"] = {};
    base["CustomViews"] = {};

    for (const [app_label, import_promise] of Object.entries(NautobotApps)) {
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
                                        getComponentFromModule(
                                            app_label,
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
                                    getComponentFromModule(app_label, component)
                                )
                            );
                        });
                        return true; // probably need to switch to using something other than map
                    }
                );
            }
        });
    }

    return base;
}

export default get_components();
