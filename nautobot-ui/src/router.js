import { useRoutes } from "react-router-dom";
import { lazy } from 'react';

import Home from "@views/Home";
import InstalledPlugins from "@views/InstalledPlugins";
import ListView from "@views/ListView";



// Placeholder for nautobot to inject code
// The idea would be to dynamicly generate this lines of codes relating to
//  nautobot_plugin_one_ui

// nautobot__inject__start
const NautobotPluginOne = lazy(() => import('@nautobot_plugin_one_ui/_app'));

// nautobot__inject__end


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
                    path: "installed-plugins",
                    element: <InstalledPlugins />
                },
                {
                    path: "nautobot-plugin-one",
                    element: <NautobotPluginOne />
                }
            ],
        },
    ]);
    return element;
}
