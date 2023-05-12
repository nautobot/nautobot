import axios from "axios";
import { useEffect } from "react";

import { useLogoutMutation } from "@utils/api";
import { useSelector } from "react-redux";
import { isLoggedInSelector, flushSessionState } from "@utils/store";

axios.defaults.withCredentials = true;
axios.defaults.xsrfCookieName = "csrftoken";
axios.defaults.xsrfHeaderName = "X-CSRFToken";

export default function Logout() {
    const isLoggedIn = useSelector(isLoggedInSelector);
    const [logout] = useLogoutMutation();

    useEffect(() => {
        if (isLoggedIn) {
            logout()
                .then(flushSessionState)
                .catch((err) => {
                    console.log(err);
                });
        }
    }, [isLoggedIn, logout]);

    return <></>;
}
