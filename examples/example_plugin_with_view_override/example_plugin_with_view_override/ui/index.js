export { default as PluginFullWidthPageComponent } from "./FullWidthPage";
export { default as ExampleAppOverrideModelView } from "./OverrideView";

const app_config = {
    full_width_components: {
        "dcim:locations": ["PluginFullWidthPageComponent"]
    },
    view_overrides: {
        "dcim:locations": {
            "retrieve": "ExampleAppOverrideModelView"
        }
    },
}

export default app_config
