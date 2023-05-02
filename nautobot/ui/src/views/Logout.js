import axios from "axios";

import { useGetSessionQuery } from "@utils/api";
import { useNavigate } from "react-router-dom";

axios.defaults.withCredentials = true;
axios.defaults.xsrfCookieName = "csrftoken";
axios.defaults.xsrfHeaderName = "X-CSRFToken";

export default function Logout() {
    const {
        data: sessionInfo,
        isSuccess: sessionLoaded,
        refetch: refetchSession,
    } = useGetSessionQuery();
    const navigate = useNavigate();

    // TODO: Places like this might be best to stick with Axios calls but we should have a generic Axios object
    //   for global cookie management, etc.
    if (sessionLoaded && sessionInfo.logged_in) {
        axios
            .get("/logout/")
            .then(() => {
                refetchSession().then(() => {
                    navigate("/login/");
                });
            })
            .catch((err) => console.log(err.detail));
    } else {
        navigate("/login/");
    }

    return <span>Logging out...</span>;
}
