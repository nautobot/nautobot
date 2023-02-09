export { default as ExamplePluginFullWidthPageComponent } from "./FullWidthPage"
export { default as ExamplePluginRetrieveViewOverride } from "./CustomView"

const plugin_config = {
    detail_tabs: {},
    full_width_components: {
        // TODO: do we really need to use the same component on both?
        "dcim:sites": ["ExamplePluginFullWidthPageComponent"],
        "dcim:devices": ["ExamplePluginFullWidthPageComponent"]
    },
    // TODO: this should be moved to example_plugin_with_view_override so that it doesn't impact testing
    view_overrides: {
        "ipam:ip-addresses": {
            "retrieve": "ExamplePluginRetrieveViewOverride"
        }
    }
}

export default plugin_config
