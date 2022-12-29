import { lazy } from "react"

import NautobotPlugins from "src/plugin_imports"


function EmptyElement() {
    return (<></>)
}

function findOrEmpty(module, key) {
    return key in module ? module[key] : EmptyElement
}

function my_import_as_function(module_name, component_name) {
    return NautobotPlugins[module_name].then(module => ({ default: findOrEmpty(module, component_name) })).catch({ default: EmptyElement })
}

function get_components() {
    var base = {}
    base["FullWidthComponents"] = {}
    base["CustomViews"] = {}

    for (const [plugin_name, import_promise] of Object.entries(NautobotPlugins)) {
        import_promise.then((value) => {
            if (value?.default?.view_overrides) {
                Object.entries(value.default.view_overrides).map(([route, views]) => {
                    Object.entries(views).map(([view_action, component]) => {
                        if (!base["CustomViews"][route]) base["CustomViews"][route] = {}
                        base["CustomViews"][route][view_action] = lazy(() => my_import_as_function(plugin_name, component))
                    })
                })
            }
            if (value?.default?.full_width_components) {
                Object.entries(value.default.full_width_components).map(([route, components]) => {
                    if (!base["FullWidthComponents"][route]) base["FullWidthComponents"][route] = []
                    components.map((component) => {
                        base["FullWidthComponents"][route].push(lazy(() => my_import_as_function(plugin_name, component)))
                    })
                })
            }
        })
    }

    return base;
}

export default get_components();
