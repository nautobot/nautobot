export { default as PluginFullWidthPageComponent } from "./FullWidthPage";
export { default as ExamplePluginRetrieveViewOverride } from "./CustomView"
export { default as ExamplePluginNonModelView } from "./NonModelView"

const app_config = {
    full_width_components: {
        "dcim:sites": ["PluginFullWidthPageComponent"]
    },
    view_overrides: {
        "example-plugin:models": {
            "retrieve": "ExamplePluginRetrieveViewOverride"
        }
    },
}

export default app_config
