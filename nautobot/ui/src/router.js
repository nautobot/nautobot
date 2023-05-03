import { Navigate, useRoutes } from "react-router-dom";
// import { lazy } from 'react'

import { useGetSessionQuery } from "@utils/api";
import Home from "@views/Home";
import CreateView from "@views/generic/ObjectCreate";
import DetailView from "@views/generic/ObjectRetrieve";
import ListView from "@views/generic/ObjectList";
import InstalledApps from "@views/InstalledApps";
import Login from "@views/Login";
import Logout from "@views/Logout";

// TODO: Dynamic route injection
export default function NautobotRouter() {
    const { data: sessionInfo, isSuccess: sessionLoaded } =
        useGetSessionQuery();

    let element = useRoutes([
        {
            path: "/login/",
            element: <Login />,
        },
        {
            path: "/logout/",
            element: <Logout />,
        },
        {
            path: "/",
            element:
                sessionLoaded && !sessionInfo.logged_in ? (
                    <Navigate to="/login/" />
                ) : (
                    ""
                ),
            children: [
                {
                    path: "",
                    element: <Home />,
                    children: [],
                },
                {
                    path: "/:app_name/:model_name/",
                    element: <ListView />,
                    children: [],
                },
                {
                    path: "/:app_name/:model_name/add/",
                    element: <CreateView />,
                    children: [],
                },
                {
                    path: "/:app_name/:model_name/:object_id/",
                    element: <DetailView />,
                    children: [],
                },
                {
                    path: "/plugins/",
                    children: [
                        {
                            path: "installed-plugins/",
                            element: <InstalledApps />,
                        },
                        {
                            path: ":app_name/:model_name/",
                            element: <ListView />,
                            children: [],
                        },
                        {
                            path: ":app_name/:model_name/add/",
                            element: <CreateView />,
                            children: [],
                        },
                        {
                            path: ":app_name/:model_name/:object_id/",
                            element: <DetailView />,
                            children: [],
                        },
                    ],
                },
            ],
        },
    ]);
    return element;
}
