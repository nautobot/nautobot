export { default as ExampleAppFullWidthPageComponent } from "./FullWidthPage"
export { default as ExampleAppOverrideModelView } from "./ModelView"

const app_config = {
    detail_tabs: {},
    full_width_components: {
        "dcim:devices": ["ExampleAppFullWidthPageComponent"]
    },
    view_overrides: {
        "example-plugin:other-models": {
            "retrieve": "ExampleAppOverrideModelView"
        },
    }
}

export default app_config
