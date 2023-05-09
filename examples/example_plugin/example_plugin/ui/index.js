export { default as ExampleAppFullWidthPageComponent } from "./FullWidthPage"
export { default as ExamplePluginRetrieveViewOverride } from "./RetrieveView"

const app_config = {
    detail_tabs: {},
    full_width_components: {
        "dcim:devices": ["ExampleAppFullWidthPageComponent"]
    },
    view_overrides: {
        "dcim:platforms": {
            "retrieve": "ExamplePluginRetrieveViewOverride"
        }
    }
}

export default app_config
