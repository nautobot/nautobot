export { default as PluginFullWidthPageComponent } from "./FullWidthPage.jsx";
export { default as ExamplePluginRetrieveViewOverride } from "./CustomView"

const plugin_config = {
    full_width_components: {
        "dcim:sites": ["PluginFullWidthPageComponent"]
    },
    view_overrides: {
        // TODO: this will still cause test failures since the tests run with this plugin included.
        // Needs to override an otherwise untested view instead, probably something from example-plugin?
        "ipam:ip-addresses": {
            "retrieve": "ExamplePluginRetrieveViewOverride"
        }
    }
}

export default plugin_config
