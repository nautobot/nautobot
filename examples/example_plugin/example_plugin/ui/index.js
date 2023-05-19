export { default as ExampleAppFullWidthPageComponent } from "./FullWidthPage"
export { default as ExampleAppCustomRouteView } from "./CustomRouteView"

const app_config = {
    detail_tabs: {},
    full_width_components: {
        "dcim:sites": ["ExampleAppFullWidthPageComponent"]
    },
    view_overrides: {},
    /**
     * The key of `routes_view_components` is the name of the url path,
     * and the value is the View Component that should be associated with that url path.
     */
    routes_view_components: {
        "home": "ExampleAppCustomRouteView",
    }
}

export default app_config
