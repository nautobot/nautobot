import axios from "axios";
import { useState } from "react";
import {
    Button,
    FormControl,
    FormLabel,
    Input,
    Textarea,
} from "@chakra-ui/react";

import {
    Modal,
    ModalBody,
    ModalCloseButton,
    ModalContent,
    ModalFooter,
    ModalHeader,
    ModalOverlay,
    useToast,
} from "@nautobot/nautobot-ui";
import packageJson from "../../package.json";

export default function FeedbackModal({ isOpen, onClose }) {
    const [feedbackFormState, setFeedbackFormState] = useState({});

    const feedbackToast = useToast({
        duration: 5000,
        isClosable: true,
        position: "top-right",
    });

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
            view_name: window.location.pathname,
            // TODO: Add unittest to ensure version on package.json matches version in pyproject.toml
            nautobot_version: packageJson.version,
            ...feedbackFormState,
        };

        axios
            .post(
                "https://nautobot.cloud/api/nautobot/feature-request/",
                formData
            )
            .then(() => {
                onClose();
                feedbackToast({
                    title: "Thank you for your feedback!",
                    status: "success",
                });
            })
            .catch((err) => {
                console.log(err);
                onClose();
                feedbackToast({
                    title: "Sorry, an error occurred when sending your feedback. Please try again later.",
                    status: "error",
                });
            });
    }

    return (
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
                            <FormLabel>Your email address (optional)</FormLabel>
                            <Input
                                type="email"
                                name="email"
                                onChange={changeFeedbackInputValue}
                            />
                        </FormControl>

                        <FormControl mt={4} isRequired>
                            <FormLabel>Feedback</FormLabel>
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
    );
}
