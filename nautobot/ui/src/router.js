import { useRoutes } from "react-router-dom";
// import { lazy } from 'react'

import Home from "@views/Home";
import CreateView from "@views/generic/ObjectCreate";
import DetailView from "@views/generic/ObjectRetrieve";
import GraphQLObjectRetrieve from "@views/generic/GraphQLObjectRetrieve";
import ListView from "@views/generic/ObjectList";
import InstalledApps from "@views/InstalledApps";
import Login from "@views/Login";
import Logout from "@views/Logout";

// TODO: Dynamic route injection
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
            path: "/logout/",
            element: <Logout />,
        },
        {
            path: "/:app_name/:model_name",
            element: <ListView />,
            children: [],
        },
        {
            path: "/:app_name/:model_name/add",
            element: <CreateView />,
            children: [],
        },
        {
            path: "/:app_name/:model_name/:object_id",
            element: <DetailView />,
            children: [],
        },
        {
            path: "graphql-ui/:app_name/:model_name/:object_id",
            element: <GraphQLObjectRetrieve />,
            children: [],
        },
        {
            path: "/plugins/",
            children: [
                {
                    path: "installed-plugins",
                    element: <InstalledApps />,
                },
            ],
        },
    ]);
    return element;
}
