import { faCalendarPlus, faPencil } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useDisclosure } from "@chakra-ui/react"; // TODO: use nautobot-ui when available
import {
    Box,
    Button as UIButton,
    ButtonGroup,
    Heading,
    Text,
    MeatballsIcon,
    Modal,
    ModalBody,
    ModalCloseButton,
    ModalContent,
    ModalOverlay,
    NtcThumbnailIcon,
} from "@nautobot/nautobot-ui";

import { ReferenceDataTag } from "@components/ReferenceDataTag";
import { humanFriendlyDate } from "@utils/date";

export default function RenderHeader({ data }) {
    const { isOpen, onClose, onOpen } = useDisclosure();
    return (
        <Box display="flex" justifyContent="space-between" padding="md">
            <Heading display="flex" alignItems="center" gap="5px">
                {/* TODO(Timizuo): Create a reusable component from <Heading><NtcThumbnailIcon /> {title}</Heading> */}
                <NtcThumbnailIcon width="25px" height="30px" />{" "}
                <Text size="H1" as="h1">
                    {data.display}
                </Text>
                {data.status && (
                    <Box p={2} flexGrow="1">
                        <Text size="P2">
                            <ReferenceDataTag
                                model_name="statuses"
                                id={data.status.id}
                                variant="unknown"
                                size="sm"
                            />
                        </Text>
                    </Box>
                )}
                {data.created && (
                    <Box p={2} flexGrow="1">
                        <Text size="P2" color="gray-2">
                            <FontAwesomeIcon icon={faCalendarPlus} />
                            {humanFriendlyDate(data.created)}
                        </Text>
                    </Box>
                )}
                {data.last_updated && (
                    <Box p={2} flexGrow="1">
                        <Text size="P2" color="gray-2">
                            <FontAwesomeIcon icon={faPencil} />
                            {humanFriendlyDate(data.last_updated)}
                        </Text>
                    </Box>
                )}
            </Heading>
            <ButtonGroup alignItems="center">
                <UIButton
                    size="sm"
                    variant="primaryAction"
                    leftIcon={<MeatballsIcon />}
                    onClick={onOpen}
                >
                    Actions
                </UIButton>

                <Modal isOpen={isOpen} onClose={onClose}>
                    <ModalOverlay />

                    <ModalContent>
                        <ModalCloseButton />

                        <ModalBody>To be implemented!</ModalBody>
                    </ModalContent>
                </Modal>
            </ButtonGroup>
        </Box>
    );
}
