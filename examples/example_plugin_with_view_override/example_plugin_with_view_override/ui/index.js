export { default as PluginFullWidthPageComponent } from "./FullWidthPage";
export { default as ExamplePluginOverridenModelView } from "./OverridenView";

const app_config = {
    full_width_components: {
        "dcim:locations": ["PluginFullWidthPageComponent"]
    },
    view_overrides: {
        "dcim:locations": {
            "retrieve": "ExamplePluginOverridenModelView"
        }
    },
}

export default app_config
