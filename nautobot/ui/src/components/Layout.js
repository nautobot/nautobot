import { useSelector } from "react-redux";
import { useEffect, useState } from "react";
import {
    Box,
    Flex,
    Heading,
    Link,
    NautobotLogoIcon,
    Sidebar,
    Button,
    useDisclosure,
} from "@nautobot/nautobot-ui";
import axios from "axios";

import RouterLink from "@components/RouterLink";
import SidebarNav from "@components/SidebarNav";
import { isLoggedInSelector } from "@utils/store";
import FeedbackModal from "@components/FeedbackModal";

export default function Layout({ children }) {
    const isLoggedIn = useSelector(isLoggedInSelector);

    const { isOpen, onOpen, onClose } = useDisclosure();
    const [showFeedback, setShowFeedback] = useState(false);

    useEffect(() => {
        axios
            .get("/api/ui/settings/?name=FEEDBACK_BUTTON_ENABLED")
            .then((res) => setShowFeedback(res.data.FEEDBACK_BUTTON_ENABLED))
            .catch((err) => console.error(err));
    }, []);

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
                <Box flex="1">{isLoggedIn && <SidebarNav />}</Box>
                <Box borderTop="2px" borderColor="gray.500">
                    {showFeedback && (
                        <Button onClick={onOpen} variant="link" color="gray-1">
                            Submit Feedback
                        </Button>
                    )}
                    <Button onClick={legacyUI} variant="link" color="gray-1">
                        Return to Legacy UI
                    </Button>
                </Box>
            </Sidebar>

            <Box flex="1" height="full">
                {children}
            </Box>

            <FeedbackModal isOpen={isOpen} onClose={onClose} />
        </Flex>
    );
}
