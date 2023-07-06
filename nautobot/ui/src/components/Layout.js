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
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalFooter,
    ModalBody,
    ModalCloseButton,
    useDisclosure,
    FormControl,
    FormLabel,
    Input,
    useToast,
} from "@nautobot/nautobot-ui";
import { Textarea } from "@chakra-ui/react";
import axios from "axios";

import packageJson from "../../package.json";
import RouterLink from "@components/RouterLink";
import SidebarNav from "@components/SidebarNav";
import { isLoggedInSelector } from "@utils/store";

export default function Layout({ children }) {
    const isLoggedIn = useSelector(isLoggedInSelector);
    const [feedbackFormState, setFeedbackFormState] = useState({});
    const { isOpen, onOpen, onClose } = useDisclosure();
    const [showFeedback, setShowFeedback] = useState(false);

    useEffect(() => {
        axios
            .get("/api/ui/get-settings/?name=FEEDBACK_BUTTON_ENABLED")
            .then((res) => setShowFeedback(res.data.FEEDBACK_BUTTON_ENABLED))
            .catch((err) => console.error(err));
    }, []);

    const feedbackToast = useToast({
        duration: 5000,
        isClosable: true,
        position: "top-right",
    });

    /** Invalidate the newui cookie and reload the page in order to return to the legacy UI. */
    function legacyUI() {
        document.cookie =
            "newui=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        document.location.reload(true);
    }

    function changeFeedbackInputValue(e) {
        setFeedbackFormState((state) => ({
            ...state,
            [e.target.name]: e.target.value,
        }));
    }

    function handleLeaveFeedbackSubmit(e) {
        e.preventDefault();
        const formData = {
            user_agent: navigator.userAgent,
            view_name: "home",
            nautobot_version: packageJson.version,
            ...feedbackFormState,
        };
        const url = "https://nautobot.cloud/api/nautobot/feature-request/";
        axios
            .post(url, formData)
            .then((response) => {
                onClose();
                feedbackToast({ title: "Feedback sent!", status: "success" });
            })
            .catch((err) => {
                console.log(err);
                onClose();
                feedbackToast({ title: "Feedback not sent!", status: "error" });
            });
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

            <Modal isOpen={isOpen} onClose={onClose} id="22">
                <ModalOverlay
                    bg="blackAlpha.300"
                    backdropFilter="blur(10px)"
                    zIndex="5"
                />
                <ModalContent>
                    <form method="post" onSubmit={handleLeaveFeedbackSubmit}>
                        <ModalHeader marginTop="5" marginLeft="5">
                            Submit Feedback
                        </ModalHeader>
                        <ModalCloseButton />
                        <ModalBody pb={6}>
                            <FormControl>
                                <FormLabel>Email</FormLabel>
                                <Input
                                    type="email"
                                    name="email"
                                    onChange={changeFeedbackInputValue}
                                />
                            </FormControl>

                            <FormControl mt={4} isRequired>
                                <FormLabel>Description</FormLabel>
                                <Textarea
                                    border="1px"
                                    borderColor="gray.300"
                                    borderRadius="lg"
                                    width="full"
                                    padding="2.5px"
                                    paddingLeft="8px"
                                    required
                                    name="description"
                                    onChange={changeFeedbackInputValue}
                                    size="lg"
                                    rows={5}
                                />
                            </FormControl>
                        </ModalBody>

                        <ModalFooter justifyContent="flex-end" gap="3">
                            <Button variant="primary" type="submit">
                                Send
                            </Button>
                            <Button onClick={onClose}>Cancel</Button>
                        </ModalFooter>
                    </form>
                </ModalContent>
            </Modal>
        </Flex>
    );
}
