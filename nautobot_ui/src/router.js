import { useRoutes } from "react-router-dom";

import Home from "@views/Home";
import InstalledPlugins from "@views/InstalledPlugins";
import ListView from "@views/ListView";

import {  convertNavigationToRoute } from "./utils";



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
            path: "/plugins/",
            children: [
                {
                    path: "installed-plugins-old",
                    element: <InstalledPlugins />
                },
                // nautobot__inject_route__start

                // nautobot__inject_route__ends
            ],
        },
        // ...convertNavigationToRoute(),
    ]);
    return element;
}
