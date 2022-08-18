import ListView from "../../../common/template/list-view";
import * as Icon from 'react-feather';


export default function ExamplePluginIndex(){
    const pageConfig = {
        "buttons": {
            "import": false,
            "export": false,
            "show_all": {
                "label": "Show All",
                "icon": <Icon.Eye size={15} />,
                "color": "success",
                "link": "#"
            },
        },
        "data": require("../../../common/utils/table_example_api.json"),
        "filter_form": require("../../../common/utils/table_example_api.json")["filter_form"],
    }

    return (
        <ListView config={pageConfig} />
    )
}