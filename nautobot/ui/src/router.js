import { Navigate, useRoutes } from "react-router-dom";
import { useGetSessionQuery } from "@utils/api";
import Home from "@views/Home";
import CreateView from "@views/generic/ObjectCreate";
import DetailView from "@views/generic/ObjectRetrieve";
import ListView from "@views/generic/ObjectList";
import InstalledApps from "@views/InstalledApps";
import Login from "@views/Login";
import Logout from "@views/Logout";
import { getPluginRoutes } from "@utils";

// TODO: Dynamic route injection
export default function NautobotRouter() {
    const {
        data: sessionInfo,
        isSuccess: sessionLoaded,
        isError: sessionError,
    } = useGetSessionQuery();

    return useRoutes([
        {
            path: "/login/",
            element:
                sessionError || (sessionLoaded && !sessionInfo.logged_in) ? (
                    <Login />
                ) : (
                    <Navigate to="/" />
                ),
        },
        {
            path: "/logout/",
            element: <Logout />,
        },
        {
            path: "/",
            element:
                sessionError ||
                (sessionLoaded && !sessionInfo.logged_in && (
                    <Navigate to="/login/" />
                )),
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
                        ...getPluginRoutes(),
                    ],
                },
            ],
        },
    ]);
}
