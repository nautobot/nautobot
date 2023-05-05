import { DynamicChoiceWidget, DynamicMultiChoiceWidget } from "@components/form_widgets"




const uiSchema = {
    // "ui:options": {
    //     "style": {
    //         "columns": "3",
    //         "columnGap": "2rem"
    //     }
    // },
    // "Location": {
    //     "location": {
    //         "ui:widget": "DynamicChoiceField",
    //     },
    // }
    // ,
    // "Tags": {
    //     "tags": {
    //         "ui:widget": "DynamicMultipleChoiceField",
    //     },
    // }
}

const widget = {
    DynamicChoiceField: DynamicChoiceWidget,
    DynamicMultipleChoiceField: DynamicMultiChoiceWidget,
}

export {uiSchema, widget};