export { default as ExampleAppFullWidthPageComponent } from "./FullWidthPage"
export { default as ExampleAppOverrideModelView } from "./ModelView"
export { default as ExampleAppNonModelView } from "./NonModelView"

const app_config = {
    detail_tabs: {},
    full_width_components: {
        "dcim:devices": ["ExampleAppFullWidthPageComponent"]
    },
    view_overrides: {
        "example-plugin:other-models": {
            "retrieve": "ExampleAppOverrideModelView"
        },
    },
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
                            component: "ExampleAppNonModelView",
                            namespace: "non-model-view", 
                        }
                    ]
                }
            ]
        }
    ]
}

export default app_config
