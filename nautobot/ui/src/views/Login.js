import {
    Button,
    FormControl,
    FormLabel,
    Input,
    Box,
    Spinner,
} from "@nautobot/nautobot-ui";

import { useGetSessionQuery, useLoginMutation } from "@utils/api";

export default function Login() {
    const { refetch: refetchSession } = useGetSessionQuery();
    const [login, { isLoading }] = useLoginMutation();

    /** Handle the form submission. */
    const handleSubmit = (e) => {
        e.preventDefault();
        login({
            username: e.target.username.value,
            password: e.target.password.value,
        })
            .then(refetchSession)
            .catch(console.log);
    };

    return (
        <Box boxShadow="base" p="6" rounded="md" bg="white">
            {/* Show that we're trying to log in while we wait for the server to respond. */}
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
