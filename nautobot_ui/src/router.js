import { useRoutes } from "react-router-dom"
// import { lazy } from 'react'

import Home from "@views/Home"
import DetailView from "@views/generic/ObjectRetrieve"
import InstalledPlugins from "@views/InstalledPlugins"
import ListView from "@views/generic/ObjectList"
import Login from "@views/Login"



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
            path: "/login/",
            element: <Login />,
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
        {
            path: "/plugins/",
            children: [
                {
                    path: "installed-plugins",
                    element: <InstalledPlugins />
                }
            ],
        },
    ]);
    return element;
}
//////
