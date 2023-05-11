export { default as PluginFullWidthPageComponent } from "./FullWidthPage";
export { default as ExamplePluginRetrieveViewOverride } from "./CustomView"
export { default as ExamplePluginNonModelView } from "./NonModelView"

const app_config = {
    full_width_components: {
        "dcim:sites": ["PluginFullWidthPageComponent"]
    },
    view_overrides: {
        // TODO: this will still cause test failures since the tests run with this plugin included.
        // Needs to override an otherwise untested view instead, probably something from example-plugin?
        "ipam:ip-addresses": {
            "retrieve": "ExamplePluginRetrieveViewOverride"
        }
    },
    routes: [
        {
            component: "ExamplePluginNonModelView",
            // This would be used as this route namespace; similar to what we have in django; "<app_name>:<namespace>"
            namespace: "non-model-view", 
            name: "Inventory",
            groups: [
                {
                    name: "Example App With View Override",
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
