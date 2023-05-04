import AsyncSelect from 'react-select/async';
import { useGetRESTAPIQuery } from "@utils/api";

const colourStyles = {
    control: (styles) => ({ ...styles }),
    option: (styles, { data, isDisabled, isFocused, isSelected }) => ({...styles, color:"#000"}),
    multiValue: (styles, { data }) => ({...styles, color: "#fff"}),
    multiValueLabel: (styles, { data }) => ({...styles, color: "#fff", backgroundColor: data.color}),
    multiValueRemove: (styles, { data }) => ({...styles, color: "#fff", backgroundColor: data.color}),
};


const DynamicChoiceField = ({isMulti, ...props}) => {
    const {app_name, model_name} = props.schema.additionalProps;
    let searchQuery = {app_name, model_name, depth: 0};
    let extra_props = {}
    const { data: listData, isLoading: listDataLoading } = useGetRESTAPIQuery(searchQuery);
    
    const loadOptions = (inputValue, callback) => {
        if (listData) {
            const data = listData.results.map(item => { return {
                value: item.id,
                label: item.display,
                color: item.color ? "#" + item.color : "",
                backgroundColor: item.color ? "#" + item.color : "",
            }})
            callback(data);
        }
    };
    if (isMulti) {
        extra_props.isMulti = true;
    }

    return <AsyncSelect cacheOptions loadOptions={loadOptions} defaultOptions {...extra_props} styles={colourStyles} />
}

const DynamicMultipleChoiceField = (props) => {
    return <DynamicChoiceField isMulti={true} {...props} />
}

const uiSchema = {
    "ui:options": {
        "style": {
            "columns": "3",
            "columnGap": "2rem"
        }
    },
    "Location": {
        "location": {
            "ui:widget": "DynamicChoiceField",
        },
    }
    ,
    "Tags": {
        "tags": {
            "ui:widget": "DynamicMultipleChoiceField",
        },
    }
}

const widget = {
    DynamicChoiceField: DynamicChoiceField,
    DynamicMultipleChoiceField: DynamicMultipleChoiceField,
}

export {uiSchema, widget};