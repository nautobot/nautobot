export { default as ExamplePluginFullWidthPageComponent } from "./FullWidthPage"

const plugin_config = {
    detail_tabs: {},
    full_width_components: {
        "dcim:sites": ["ExamplePluginFullWidthPageComponent"]
    },
    view_overrides: {}
}

export default plugin_config
