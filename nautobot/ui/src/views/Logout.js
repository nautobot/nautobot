import axios from "axios";
import { useEffect } from "react";

import { useLogoutMutation } from "@utils/api";
import { useSelector, useDispatch } from "react-redux";
import { isLoggedInSelector, flushSessionState } from "@utils/store";

axios.defaults.withCredentials = true;
axios.defaults.xsrfCookieName = "csrftoken";
axios.defaults.xsrfHeaderName = "X-CSRFToken";

export default function Logout() {
    const isLoggedIn = useSelector(isLoggedInSelector);
    const [logout] = useLogoutMutation();
    const dispatch = useDispatch();

    useEffect(() => {
        if (isLoggedIn) {
            logout()
                .then(dispatch(flushSessionState()))
                .catch((err) => {
                    console.log(err);
                });
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps -- only run on mount

    return <></>;
}
