import {createBrowserRouter} from "react-router-dom";

import Home from "./views/Home";
import Plugins from "./views/Plugins";


const router = createBrowserRouter([
    {
        path: "/",
        element: <Home />,
    },
    {
        path: "/plugins",
        element: <Plugins />,
        children: [
            // Add plugins path here
        ]
    },
]);

export default router;
