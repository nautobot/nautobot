export { default as ExamplePluginFullWidthPageComponent } from "./FullWidthPage"
export { default as ExamplePluginRetrieveViewOverride } from "./CustomView"

const plugin_config = {
    detail_tabs: {},
    full_width_components: {
        "dcim:sites": ["ExamplePluginFullWidthPageComponent"],
        "dcim:devices": ["ExamplePluginFullWidthPageComponent"]
    },
    view_overrides: {
        "ipam:ip-addresses": {
            "retrieve": "ExamplePluginRetrieveViewOverride"
        }
    }
}

export default plugin_config
