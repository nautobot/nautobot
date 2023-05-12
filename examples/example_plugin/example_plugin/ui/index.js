export { default as ExampleAppFullWidthPageComponent } from "./FullWidthPage"
export { default as ExamplePluginNonModelView } from "./NonModelView"

const app_config = {
    detail_tabs: {},
    full_width_components: {
        "dcim:devices": ["ExampleAppFullWidthPageComponent"]
    },
    view_overrides: {},
    routes: [
        {
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
                            component: "ExamplePluginNonModelView",
                            namespace: "non-model-view", 
                        }
                    ]
                }
            ]
        }
    ]
}

export default app_config
