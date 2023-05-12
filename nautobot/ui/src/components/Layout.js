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

import LoadingWidget from "@components/LoadingWidget";
import RouterLink from "@components/RouterLink";
import SidebarNav from "@components/SidebarNav";
import { useGetSessionQuery, useGetUIMenuQuery } from "@utils/api";
import { useSelector } from "react-redux";
import { isLoggedInSelector } from "@utils/store";

export default function Layout({ children }) {
    const isLoggedIn = useSelector(isLoggedInSelector);
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

    // TODO: showing the loading widget while the menu is loading is breaking the login route if not logged into the backend server
    // if (!sessionLoaded || !menuLoaded || sessionInfo === undefined)
    //     toRender = <LoadingWidget name="application" />;

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
            <Sidebar overflow="hidden">
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
                {isLoggedIn && <SidebarNav />}
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
