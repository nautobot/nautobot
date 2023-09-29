import { Navigate, useRoutes } from "react-router-dom";
import { useSelector } from "react-redux";
import { isLoggedInSelector } from "@utils/store";
import CreateView from "@views/generic/ObjectCreate";
import DetailView from "@views/generic/ObjectRetrieve";
import ListView from "@views/generic/ObjectList";
import Home from "@views/Home";
import InstalledApps from "@views/InstalledApps";
import Login from "@views/Login";
import Logout from "@views/Logout";
import { getPluginRoutes } from "@utils";

export default function NautobotRouter() {
    const isLoggedIn = useSelector(isLoggedInSelector);

    return useRoutes([
        {
            path: "/login/",
            element: !isLoggedIn ? <Login /> : <Navigate to="/" />,
        },
        {
            path: "/logout/",
            element: isLoggedIn ? <Logout /> : <Navigate to="/login/" />,
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
                    path: "/:app_label/:model_name/",
                    element: <ListView />,
                    children: [],
                },
                {
                    path: "/:app_label/:model_name/add/",
                    element: <CreateView />,
                    children: [],
                },
                {
                    path: "/:app_label/:model_name/:object_id/",
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
                            path: ":app_label/:model_name/",
                            element: <ListView />,
                            children: [],
                        },
                        {
                            path: ":app_label/:model_name/add/",
                            element: <CreateView />,
                            children: [],
                        },
                        {
                            path: ":app_label/:model_name/:object_id/",
                            element: <DetailView />,
                            children: [],
                        },
                        ...getPluginRoutes(),
                    ],
                },
            ],
        },
    ]);
}
