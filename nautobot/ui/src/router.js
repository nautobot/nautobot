import { Navigate, useRoutes } from "react-router-dom";
// import { lazy } from 'react'

import { useSelector } from "react-redux";
import { isLoggedInSelector } from "@utils/store";
import Home from "@views/Home";
import CreateView from "@views/generic/ObjectCreate";
import DetailView from "@views/generic/ObjectRetrieve";
import ListView from "@views/generic/ObjectList";
import InstalledApps from "@views/InstalledApps";
import Login from "@views/Login";
import Logout from "@views/Logout";

// TODO: Dynamic route injection
export default function NautobotRouter() {
    const isLoggedIn = useSelector(isLoggedInSelector);

    let element = useRoutes([
        {
            path: "/login/",
            element: !isLoggedIn ? <Login /> : <Navigate to="/" />,
        },
        {
            path: "/logout/",
            element: isLoggedIn ? <Logout /> : <Navigate to="/" />,
        },
        {
            path: "/",
            element: !isLoggedIn && <Navigate to="/login/" />,
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
