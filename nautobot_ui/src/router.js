import { useRoutes } from "react-router-dom";
// import { lazy } from 'react';

import Home from "@views/BSHome";
import ListView from "@views/BSListView";
import DetailView from "@views/BSDetailView";



// Placeholder for nautobot to inject code
// The idea would be to dynamically generate this lines of codes relating to
//  nautobot_plugin_one_ui

// nautobot__inject_import__start

// nautobot__inject_import__ends


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
            path: "/:app_name/:model_name/:object_id",
            element: <DetailView />,
            children: [],
        },
    ]);
    return element;
}
