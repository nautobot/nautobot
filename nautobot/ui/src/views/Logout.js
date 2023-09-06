import { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";

import { useLogoutMutation } from "@utils/api";
import { isLoggedInSelector, flushSessionState } from "@utils/store";

export default function Logout() {
    const isLoggedIn = useSelector(isLoggedInSelector); // While the router _should_ never try to render this view if we aren't logged in, we should still check.
    const [logout] = useLogoutMutation();
    const dispatch = useDispatch();

    /** Log out only when mounting the component, we should be logged out by the time it tries to render. */
    useEffect(() => {
        if (isLoggedIn) {
            logout().then(dispatch(flushSessionState())).catch(console.log);
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps -- only run on mount

    return <></>;
}
