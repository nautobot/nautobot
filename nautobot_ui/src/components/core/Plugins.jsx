import { lazy } from "react"

import NautobotPlugins from "../../plugin_imports"

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
    base["FullWidthComponents"] = []
    base["CustomViews"] = {"dcim:sites": null}

    for (const [plugin_name, import_promise] of Object.entries(NautobotPlugins)) {
        base["FullWidthComponents"].push(lazy(() => my_import_as_function(plugin_name, 'PluginFullWidthPageComponent')))
    }

    for (const [plugin_name, import_promise] of Object.entries(NautobotPlugins)) {
        base["CustomViews"]["dcim:sites"] = lazy(() => my_import_as_function(plugin_name, 'PluginCustomView'))
    }

    return base;
}

export default get_components();