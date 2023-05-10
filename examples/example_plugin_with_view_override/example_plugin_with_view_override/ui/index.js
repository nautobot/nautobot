export { default as PluginFullWidthPageComponent } from "./FullWidthPage.jsx";
// export { default as ExamplePluginRetrieveViewOverride } from "./CustomView";
export { default as ExamplePluginRetrieveViewOverride } from "./RetrieveView";

const plugin_config = {
    full_width_components: {
        "dcim:sites": ["PluginFullWidthPageComponent"]
    },
    view_overrides: {
        "example-plugin:models": {
            "retrieve": "ExamplePluginRetrieveViewOverride"
        }
    }
}

export default plugin_config
