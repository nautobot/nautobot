export { default as ExampleAppFullWidthPageComponent } from "./FullWidthPage"
export { default as ExampleAppCustomRouteView } from "./CustomRouteView"
export { default as ExampleAppOverrideModelView } from "./ModelView"

const app_config = {
    detail_tabs: {},
    full_width_components: {
        "dcim:devices": ["ExampleAppFullWidthPageComponent"]
    },
    /**
     * The key of 'routes_view_components' is the app's base_url:url_name, 
     * and the value is the View Component associated with that url path.
     */
    routes_view_components: {
        "example-plugin:home": "ExampleAppCustomRouteView",
    },
    view_overrides: {
        "example-plugin:other-models": {
            "retrieve": "ExampleAppOverrideModelView"
        },
    }
}

export default app_config
