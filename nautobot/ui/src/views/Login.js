import {
    Button,
    FormControl,
    FormLabel,
    Input,
    Box,
    Spinner,
} from "@nautobot/nautobot-ui";
import axios from "axios";

import { useGetSessionQuery, useLoginMutation } from "@utils/api";
import { useNavigate } from "react-router-dom";

axios.defaults.withCredentials = true;
axios.defaults.xsrfCookieName = "csrftoken";
axios.defaults.xsrfHeaderName = "X-CSRFToken";

export default function Login() {
    const { refetch: refetchSession } = useGetSessionQuery();
    const [login, { isLoading }] = useLoginMutation();
    const navigate = useNavigate();

    // TODO: Places like this might be best to stick with Axios calls but we should have a generic Axios object
    //   for global cookie management, etc.
    const handleSubmit = (e) => {
        login({
            username: e.target.username.value,
            password: e.target.password.value,
        })
            .then(refetchSession)
            .catch((err) => {
                console.log("error");
                console.log(err);
            });
        e.preventDefault();
        // axios
        //     .post("/api/users/tokens/authenticate/", {
        //         username: e.target.username.value,
        //         password: e.target.password.value,
        //     })
        //     .then(() => {
        //         refetchSession().then(() => {
        //             navigate("/");
        //         });
        //     })
        //     .catch((err) =>
        //         alert(err.response?.data?.non_field_errors || err.message)
        //     );
    };

    return (
        <Box boxShadow="base" p="6" rounded="md" bg="white">
            {isLoading && <Spinner />}
            <form method="POST" onSubmit={handleSubmit}>
                <FormControl>
                    <FormLabel>Username</FormLabel>
                    <Input isRequired={true} name="username"></Input>
                </FormControl>
                <FormControl>
                    <FormLabel>Password</FormLabel>
                    <Input
                        isRequired={true}
                        name="password"
                        type="password"
                    ></Input>
                </FormControl>
                <Button type="submit">Log In</Button>
            </form>
        </Box>
    );
}

// TODO: This should be all that's needed to support SSO backends but doesn't work well with NodeJS dev mode for the time being
//   Has worked with built version served by Django
// { isSuccess && sessionInfo.backends.length > 0 ?
//   sessionInfo.backends.map((backend, idx) => { return (<Link key={idx} href={backend}>Login with {backend}</Link>) })
// : <></> }
