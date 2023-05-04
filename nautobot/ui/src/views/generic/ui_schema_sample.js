import AsyncSelect from 'react-select/async';
import { useGetRESTAPIQuery } from "@utils/api";



const AsyncWidget = (props) => {
    const {app_name, model_name} = props.schema.additionalProps;
    let searchQuery = {app_name, model_name, depth: 0};
    const { data: listData, isLoading: listDataLoading } = useGetRESTAPIQuery(searchQuery);
    
    const loadOptions = (inputValue, callback) => {
        if (listData) {
            const data = listData.results.map(item => { return {
                value: item.id,
                label: item.display
            }})
            callback(data);
        }
    };

    return <AsyncSelect cacheOptions loadOptions={loadOptions} defaultOptions />
}

const uiSchema = {
    "Location": {
        "location": {
            "ui:widget": "AsyncWidget"
        }
    }
}

const widget = {
    AsyncWidget: AsyncWidget,
}

export {uiSchema, widget};