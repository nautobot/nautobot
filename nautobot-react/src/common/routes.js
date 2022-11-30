import App from "App";
import ListViewTemplate from "./template/ListViewTemplate";
import ObjectRetrieveTemplate from "./template/ObjectRetrieveTemplate";

const core_routes = [
    {
        path: "/",
        element: <App />,
    },
    {
        path: "/dcim/sites",
        element: <ListViewTemplate />,
    },
    {
        path: "/dcim/sites/:id",
        element: <ObjectRetrieveTemplate />,
    },
]

export default core_routes;
