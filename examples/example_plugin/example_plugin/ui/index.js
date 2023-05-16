export { default as ExampleAppFullWidthPageComponent } from "./FullWidthPage"
export { default as ExampleAppModelRetrieveView } from "./ModelRetrieveView"

const app_config = {
    detail_tabs: {},
    full_width_components: {
        "dcim:sites": ["ExampleAppFullWidthPageComponent"]
    },
    view_overrides: {},
    routes_view_components: {
        "examplemodel": "ExampleAppModelRetrieveView",
    }
}

export default app_config
