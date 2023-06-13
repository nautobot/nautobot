import { useSelector } from "react-redux";
import {
    Box,
    Flex,
    Heading,
    Link,
    NautobotLogoIcon,
    Sidebar,
    Button,
} from "@nautobot/nautobot-ui";

import RouterLink from "@components/RouterLink";
import SidebarNav from "@components/SidebarNav";
import { isLoggedInSelector } from "@utils/store";

export default function Layout({ children }) {
    const isLoggedIn = useSelector(isLoggedInSelector);

    /** Invalidate the newui cookie and reload the page in order to return to the legacy UI. */
    function legacyUI() {
        document.cookie =
            "newui=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        document.location.reload(true);
    }

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
                <Button onClick={legacyUI} variant="link" color="gray-1">
                    Return to Legacy UI
                </Button>
            </Sidebar>

            <Box flex="1" height="full">
                {children}
            </Box>
        </Flex>
    );
}
