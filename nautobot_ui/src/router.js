import { useRoutes } from "react-router-dom";

import Home from "@views/Home";
import InstalledPlugins from "@views/InstalledPlugins";
import ListView from "@views/ListView";

import {  definedRoutes } from "./utils";




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
            ],
        },
        ...definedRoutes,
    ]);
    return element;
}
