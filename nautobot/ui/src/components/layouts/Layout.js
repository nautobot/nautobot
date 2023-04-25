import {
    Box,
    Flex,
    Heading,
    Link,
    NautobotLogoIcon,
    Sidebar,
    Button,
} from "@nautobot/nautobot-ui";

import { useEffect } from "react";

import LoadingWidget from "@components/common/LoadingWidget";
import RouterButton from "@components/common/RouterButton";
import RouterLink from "@components/common/RouterLink";
import SidebarNav from "@components/common/SidebarNav";
import { useGetSessionQuery, useGetUIMenuQuery } from "@utils/api";

export default function Layout({ children }) {
    const { data: sessionInfo, isSuccess: sessionLoaded } =
        useGetSessionQuery();
    const { isSuccess: menuLoaded, refetch: refetchMenu } = useGetUIMenuQuery();

    // TODO: Update for RTK pattern hopefully
    // Here is the safest place to check that the session and menu data are loaded
    // to then regenerate the API and update what is globally known
    // import { useEffect } from "react";
    // const fullApi = generateFullAPI(menuData)
    useEffect(() => {
        refetchMenu();
    }, [refetchMenu]);

    let toRender = children;

    if (!sessionLoaded || !menuLoaded || sessionInfo === undefined)
        toRender = <LoadingWidget name="application" />;

    function legacyUI() {
        document.cookie =
            "newui=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        document.location.reload(true);
    }

    // TODO: This needs to be moved to useEffect. Weird order of operations.
    // const path = location.pathname
    // if (sessionLoaded && !sessionInfo.logged_in && path !== "/")
    //   navigate("/")

    // TODO: This layout can/should be it's own component because we mix component and data calls here
    //   Also, a lot of these styles need to be made globally generic
    //   It would save us the `toRender` above.
    return (
        <Flex height="full" overflow="hidden" width="full">
            <Sidebar>
                <Heading
                    as="h1"
                    paddingBottom="md"
                    paddingTop="29px"
                    paddingX="md"
                >
                    <Link
                        aria-label="Nautobot"
                        as={RouterLink}
                        leftIcon={<NautobotLogoIcon />}
                        to="/"
                    />
                </Heading>
                {sessionInfo && sessionInfo.logged_in ? (
                    <>
                        <SidebarNav />
                        <RouterButton m={3} to="/logout/">
                            Log Out
                        </RouterButton>
                    </>
                ) : (
                    <RouterButton m={3} to="/login/">
                        Log In
                    </RouterButton>
                )}
                <Button onClick={legacyUI} variant="link" color="white">
                    Return to Legacy UI
                </Button>
            </Sidebar>

            <Box flex="1" height="full">
                {toRender}
            </Box>
        </Flex>
    );
}
