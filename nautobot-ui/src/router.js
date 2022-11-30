import { useRoutes } from "react-router-dom";

import Home from "@views/Home";
import Plugins from "@views/Plugins";
import ListView from "@views/ListView";

export default function NautobotRouter() {
    let element = useRoutes([
        {
            path: "/",
            element: <Home />,
            children: [],
        },
        {
            path: "/:app_name/:model_name",
            element: <ListView />,
            children: [],
        },
        {
            path: "/plugins",
            element: <Plugins />,
            children: [],
        },
    ]);
    return element;
}
