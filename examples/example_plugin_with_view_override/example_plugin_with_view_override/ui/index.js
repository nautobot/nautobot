export { default as PluginFullWidthPageComponent } from "./FullWidthPage";
export { default as ExamplePluginRetrieveViewOverride } from "./CustomView"
export { default as ExamplePluginNonModelView } from "./NonModelView"

const app_config = {
    full_width_components: {
        "dcim:locations": ["PluginFullWidthPageComponent"]
    },
    view_overrides: {
        // TODO: this will still cause test failures since the tests run with this plugin included.
        // Needs to override an otherwise untested view instead, probably something from example-plugin?
        "ipam:ip-addresses": {
            "retrieve": "ExamplePluginRetrieveViewOverride"
        }
    },
}

export default app_config
