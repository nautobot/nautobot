export { default as ExampleAppFullWidthPageComponent } from "./FullWidthPage"
export { default as ExamplePluginNonModelView } from "./NonModelView"

const app_config = {
    detail_tabs: {},
    full_width_components: {
        "dcim:sites": ["ExampleAppFullWidthPageComponent"]
    },
    view_overrides: {},
    routes_view_components: {
        "examplemodel": "ExamplePluginNonModelView",
    }
}

export default app_config
