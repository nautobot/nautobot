import ListView from "../../../common/template/list-view";


export default function ExamplePluginIndex(){
    return (
        <ListView list_url={require("../../../common/utils/table_example_api.json.json")} />
    )
}