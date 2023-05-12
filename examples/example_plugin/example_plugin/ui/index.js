export { default as ExampleAppFullWidthPageComponent } from "./FullWidthPage"
export { default as ExamplePluginNonModelView } from "./NonModelView"

const app_config = {
    detail_tabs: {},
    full_width_components: {
        "dcim:sites": ["ExampleAppFullWidthPageComponent"]
    },
    view_overrides: {},
    routes: [
        {
            component: "ExamplePluginNonModelView",
            // This would be used as this route namespace; similar to what we have in django; "<app_name>:<namespace>"
            namespace: "non-model-view", 
            name: "Inventory",
            groups: [
                {
                    name: "Example App",
                    weight: 150,
                    items: [
                        {
                            name: "Non Model View",
                            weight: 100,
                            path: "/non-model-view/",
                        }
                    ]
                }
            ]
        }
    ]
}

export default app_config
